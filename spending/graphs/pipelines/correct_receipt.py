from datetime import datetime, timezone
from typing import TypedDict
import uuid

from langgraph.graph import START, END, StateGraph
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import Runnable

import db

from graphs.agents import agents, calls, schemas
from graphs.pipelines.utils import one_graph_decorator


class State(TypedDict):
    task_id: uuid.UUID
    user_input: str
    instance: schemas.ReceiptBase
    need_change: bool
    new_instance: schemas.ReceiptBase
    updated: bool


async def get_from_db(state: State):
    db_object = await db.run_operation(
        db.DbOperation.mongo(op=db.OperationType.GET),
        {"id_": state['task_id']}
    )

    normalized_receipt = schemas.NormalizedReceipt.model_validate_json(db_object)
    instance = schemas.ReceiptBase.from_normalized(normalized_receipt)

    return {"instance": instance}


async def ask_need_change(state: State):
    answer: schemas.IsNeedToChange = await calls.ask_agent_question(
        agents.is_need_to_change,
        question=state['user_input']
    )

    return {"need_change": answer.need_change}


async def route(state: State):
    return state['need_change']


async def make_new_receipt(state: State):
    instance_json = state['instance'].model_dump_json()
    question = state['user_input']

    messages = [
        AIMessage(content=instance_json),
        HumanMessage(content=question)
    ]
    new_instance: schemas.ReceiptBase = await calls.ask_agent(
        agents.update_receipt,
        messages=messages,
    )

    return {"new_instance": new_instance}


async def db_update_receipt(state: State):
    new_instance = state['new_instance']
    new_instance["updatedAt"] = datetime.now(timezone.utc)

    updated = await db.run_operation(
        db.DbOperation.mongo(op=db.OperationType.UPDATE),
        {"filter": {"id_": state['task_id']}, "data": new_instance}
    )

    return {"updated": updated}


@one_graph_decorator
def create() -> Runnable:
    graph_builder = StateGraph(State)

    graph_builder.add_node("get_from_db", get_from_db)
    graph_builder.add_node("ask_need_change", ask_need_change)
    graph_builder.add_node("make_new_receipt", make_new_receipt)
    graph_builder.add_node("db_update_receipt", db_update_receipt)

    graph_builder.add_edge(START, "get_from_db")
    graph_builder.add_edge("get_from_db", "ask_need_change")
    graph_builder.add_conditional_edges(
        "ask_need_change",
        route,
        {
            True: "make_new_receipt",
            False: END,
        }
    )
    graph_builder.add_edge("make_new_receipt", "db_update_receipt")
    graph_builder.add_edge("db_update_receipt", END)

    graph = graph_builder.compile()

    return graph
