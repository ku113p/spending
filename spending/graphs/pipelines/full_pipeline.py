from typing import TypedDict
import uuid

from langgraph.graph import START, END, StateGraph
from langgraph.store.memory import BaseStore
from langgraph.types import Checkpointer, Command, interrupt
from langchain_core.runnables import Runnable

import db, utils
from graphs.agents import schemas
from graphs.pipelines import correct_receipt, image_to_normailized_receipt, nodes, utils as pipelines_utils

logger = utils.create_logger(__name__)


class State(TypedDict):
    task_id: uuid.UUID
    image_fp: str
    normalized_receipt: schemas.NormalizedReceipt
    data: dict
    inserted_id: uuid.UUID
    user_input: str
    need_change: bool


async def prep_for_save(state: State):
    task_id = state['task_id']
    norm_rec = state['normalized_receipt']
    return {"task_id": task_id, "data": {"_id": task_id, "receipt": norm_rec.model_dump()}}


async def ask_user(state: State):
    value = interrupt({"receipt": state['normalized_receipt']})
    return {"user_input": value}


async def route(state: State):
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


def create(checkpointer: Checkpointer = None, store: BaseStore = None) -> Runnable:
    graph_builder = StateGraph(State)

    graph_builder.add_node("recognize_receipt_subgraph", image_to_normailized_receipt.create())
    graph_builder.add_node("prep_for_save", prep_for_save)
    graph_builder.add_node("save_to_db", nodes.save_to_db)
    graph_builder.add_node("ask_user", ask_user)
    graph_builder.add_node("agent_correct_subgraph", correct_receipt.create())
    graph_builder.add_node("actualize_receipt", actualize_receipt)
    
    graph_builder.add_edge(START, "recognize_receipt_subgraph")
    graph_builder.add_edge("recognize_receipt_subgraph", "prep_for_save")
    graph_builder.add_edge("prep_for_save", "save_to_db")
    graph_builder.add_edge("save_to_db", "ask_user")
    graph_builder.add_edge("ask_user", "agent_correct_subgraph")
    graph_builder.add_conditional_edges(
        "agent_correct_subgraph",
        route,
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
