import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
import enum
from functools import wraps
from typing import Awaitable, Callable, Self, TypedDict
import uuid

from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import BaseCheckpointSaver
from langgraph.store.memory import BaseStore
from langgraph.types import Command, Interrupt, interrupt
from langchain_core.runnables import Runnable

import db, utils
from graphs.agents import schemas
from graphs.pipelines import correct_receipt, image_to_normailized_receipt, nodes

logger = utils.create_logger(__name__)

_INTERRUPT_TYPE_KEY: str = "interrupt_type"


class InterruptType(enum.Enum):
    ALREADY_EXISTS = enum.auto()
    IS_IT_OK = enum.auto()
    UNKNOWN = enum.auto()

    def get_marked_data(self, data: dict) -> dict:
        return {
            _INTERRUPT_TYPE_KEY: self,
            **deepcopy(data)
        }
    
    @classmethod
    def from_data(cls, value: dict) -> Self:
        if not isinstance(value, dict):
            return InterruptType.UNKNOWN
        
        if not (data_value := value.get(_INTERRUPT_TYPE_KEY)):
            return InterruptType.UNKNOWN
        
        try:
            return cls(data_value)
        except ValueError:
            return InterruptType.UNKNOWN


class OnExistsChoice(enum.Enum):
    REWRITE = "rewrite"
    CORRECT = "correct"
    FINISH = "finish"

    @property
    def as_command(self) -> Command:
        return Command(resume=self.value)


class State(TypedDict):
    task_id: uuid.UUID
    image_fp: str
    file_hash: str
    exists_strategy: OnExistsChoice
    normalized_receipt: schemas.NormalizedReceipt | None
    data: dict
    inserted_id: uuid.UUID
    user_input: str
    need_change: bool


async def calculate_file_hash(state: State):
    file_hash = await asyncio.to_thread(lambda: utils.calculate_hash(state['image_fp']))
    return {'file_hash': file_hash}


async def check_already_exists(state: State):
    file_hash = state['file_hash']
    db_object = await db.run_operation(
        db.DbOperation.mongo(op=db.OperationType.GET),
        {"filter": {"file_hash": file_hash}}
    )

    if not db_object:
        return {"normalized_receipt": None}

    task_id = db_object["_id"]
    receipt = schemas.NormalizedReceipt.model_validate(db_object["receipt"])
    return {"task_id": task_id, "normalized_receipt": receipt}


async def if_exists_route(state: State):
    receipt = state['normalized_receipt']
    if receipt is None:
        return "new_file"
    
    return "already_exists"


async def ask_what_to_do_with_existing(state: State):
    receipt = state['normalized_receipt']
    value = interrupt(InterruptType.ALREADY_EXISTS.get_marked_data({"receipt": receipt}))
    return {"exists_strategy": OnExistsChoice(value)}


async def on_exists_route(state: State):
    return state['exists_strategy'].value


async def delete_before_new(state: State):
    task_id = state['task_id']
    deleted_count = await db.run_operation(
        db.DbOperation.mongo(op=db.OperationType.DELETE),
        {"filter": {"_id": task_id}}
    )
    was_deleted = bool(deleted_count)

    logger.info(f"{was_deleted=} | {task_id=}")


async def prep_for_save(state: State):
    task_id = state['task_id']
    norm_rec = state['normalized_receipt']
    file_hash = state['file_hash']
    return {"task_id": task_id, "data": {"_id": task_id, "file_hash": file_hash, "receipt": norm_rec.model_dump()}}


async def ask_user(state: State):
    value = interrupt(InterruptType.IS_IT_OK.get_marked_data({"receipt": state['normalized_receipt']}))
    return {"user_input": value}


async def post_correcting_route(state: State):
    if state['need_change']:
        return "ask_again"  # TODO add recursion limit
    
    return "confirmed"


async def actualize_receipt(state: State):
    db_object = await db.run_operation(
        db.DbOperation.mongo(op=db.OperationType.GET),
        {"filter": {"_id": state['task_id']}}
    )

    receipt = schemas.NormalizedReceipt.model_validate(db_object["receipt"])
    return {"normalized_receipt": receipt}


def create(checkpointer: BaseCheckpointSaver = None, store: BaseStore = None) -> Runnable:
    graph_builder = StateGraph(State)

    graph_builder.add_node("calculate_file_hash", calculate_file_hash)
    graph_builder.add_node("check_already_exists", check_already_exists)
    graph_builder.add_node("ask_what_to_do_with_existing", ask_what_to_do_with_existing)
    graph_builder.add_node("delete_before_new", delete_before_new)
    graph_builder.add_node("recognize_receipt_subgraph", image_to_normailized_receipt.create())
    graph_builder.add_node("prep_for_save", prep_for_save)
    graph_builder.add_node("save_to_db", nodes.save_to_db)
    graph_builder.add_node("ask_user", ask_user)
    graph_builder.add_node("agent_correct_subgraph", correct_receipt.create())
    graph_builder.add_node("actualize_receipt", actualize_receipt)
    
    graph_builder.add_edge(START, "calculate_file_hash")
    graph_builder.add_edge("calculate_file_hash", "check_already_exists")
    graph_builder.add_conditional_edges(
        "check_already_exists",
        if_exists_route,
        {
            "new_file": "recognize_receipt_subgraph",
            "already_exists": "ask_what_to_do_with_existing",
        }
    )
    graph_builder.add_conditional_edges(
        "ask_what_to_do_with_existing",
        on_exists_route,
        {
            OnExistsChoice.REWRITE.value: "delete_before_new",
            OnExistsChoice.CORRECT.value: "ask_user",
            OnExistsChoice.FINISH.value: END,
        }
    )
    graph_builder.add_edge("delete_before_new", "recognize_receipt_subgraph")
    graph_builder.add_edge("recognize_receipt_subgraph", "prep_for_save")
    graph_builder.add_edge("prep_for_save", "save_to_db")
    graph_builder.add_edge("save_to_db", "ask_user")
    graph_builder.add_edge("ask_user", "agent_correct_subgraph")
    graph_builder.add_conditional_edges(
        "agent_correct_subgraph",
        post_correcting_route,
        {
            "confirmed": END,
            "ask_again": "actualize_receipt",
        }
    )
    graph_builder.add_edge("actualize_receipt", "ask_user")
    
    return graph_builder.compile(checkpointer=checkpointer, store=store)


async def example(image_fp: str, redis_url: str) -> dict:
    from langgraph.checkpoint.redis.aio import AsyncRedisSaver
    from langgraph.store.redis.aio import AsyncRedisStore

    async with (
        AsyncRedisStore.from_conn_string(redis_url) as store,
        AsyncRedisSaver.from_conn_string(redis_url) as checkpointer,
    ):
        # await store.setup()
        # await checkpointer.asetup()

        graph = create(checkpointer, store)
        
        task_id = uuid.uuid4()
        logger.info(f"started {task_id=}")
        config = {"configurable": {"thread_id": task_id}}
        state = State(task_id=task_id, image_fp=image_fp)

        result = await graph.ainvoke(input=state, config=config)
        c = 0
        def user_inputs():
            yield "piatos cheese price = 102"
            while True:
                yield "everithing is ok"
        inputs = user_inputs()

        while (interrupt_list := result.get('__interrupt__')) and c < 5:
            c += 1
            logger.info(f"interrupt number={c}")
            last_interrupt = interrupt_list[-1]
            logger.info(f"len={len(interrupt_list)} | {last_interrupt=}")
            result = await graph.ainvoke(Command(resume=next(inputs)), config=config)

        logger.info(f"[{c=}]final_result:{result}")


@dataclass(frozen=True)
class FullPipelineParams:
    task_id: uuid.UUID
    image_fp: str
    checkpointer: BaseCheckpointSaver | None = None
    store: BaseStore | None = None

    @property
    def config(self) -> dict:
        return {"configurable": {"thread_id": self.task_id}}
    
    @property
    def state(self) -> State:
        return State(task_id=self.task_id, image_fp=self.image_fp)


@dataclass(frozen=True)
class InterruptInfo:
    type: InterruptType
    receipt: schemas.NormalizedReceipt

    @classmethod
    def from_interrupt(cls, value: Interrupt) -> Self:
        return cls(
            type=InterruptType.from_data(value=value.value),
            receipt=value.value['receipt']
        )


@dataclass(frozen=True)
class FullPipelineResponse:
    state: State
    interrupt_info: InterruptInfo | None = None

    @classmethod
    def from_graph_response(cls, value: State) -> Self:
        interrupt_info: InterruptInfo | None

        try:
            last_interrupt = value['__interrupt__'][-1]
            interrupt_info = InterruptInfo.from_interrupt(last_interrupt)
        except KeyError:
            interrupt_info = None
        
        return cls(state=value, interrupt_info=interrupt_info)


def as_full_pipeline_response_decorator(func: Callable[..., Awaitable[State]]):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        real_response = await func(*args, **kwargs)
        response = FullPipelineResponse.from_graph_response(real_response)
        return response
    return wrapper


@dataclass
class FullPipelineController:
    params: FullPipelineParams

    _graph: Runnable = field(init=False)

    def __post_init__(self):
        self._graph = create(checkpointer=self.params.checkpointer, store=self.params.store)

    async def start(self) -> FullPipelineResponse:
        return await self._run_graph(self.params.state)
    
    @as_full_pipeline_response_decorator
    async def _run_graph(self, invoke_input) -> dict:
        return await self._graph.ainvoke(input=invoke_input, config=self.params.config)
    
    async def on_exists_answer(self, continue_choice: OnExistsChoice) -> FullPipelineResponse:
        return await self._run_graph(continue_choice.as_command)
    
    async def on_review(self, user_input: str) -> FullPipelineResponse:
        return await self._run_graph(Command(resume=user_input))
