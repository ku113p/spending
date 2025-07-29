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
        {"filter": {"_id": state['task_id']}}
    )

    normalized_receipt = schemas.NormalizedReceipt.from_raw_mongo(db_object)
    instance = schemas.ReceiptBase.from_normalized(normalized_receipt)

    return {"instance": instance}


async def ask_need_change(state: State):
    instance_json = state['instance'].model_dump_json()
    question = state['user_input']

    messages = [
        AIMessage(content=instance_json),
        HumanMessage(content=question)
    ]

    answer: schemas.CorrectReceiptRequest = await calls.ask_agent(
        agents.correct_receipt,
        messages=messages
    )

    return {"need_change": answer.need_change, "new_instance": answer.receipt_base}


async def route(state: State):
    return state['need_change']


async def db_update_receipt(state: State):
    new_instance = state['new_instance']

    updated = await db.run_operation(
        db.DbOperation.mongo(op=db.OperationType.UPDATE),
        {"filter": {"_id": state['task_id']}, "update": {"$set": {
            "receipt.updated_at": datetime.now(timezone.utc),
            "receipt.created_at": new_instance.created_at,
            "receipt.shop": new_instance.shop.model_dump(),
            "receipt.products": list(map(schemas.BaseModel.model_dump, new_instance.products)),
            "receipt.total": new_instance.total,
        }}}
    )

    return {"updated": updated}


@one_graph_decorator
def create() -> Runnable:
    graph_builder = StateGraph(State)

    graph_builder.add_node("get_from_db", get_from_db)
    graph_builder.add_node("ask_need_change", ask_need_change)
    graph_builder.add_node("db_update_receipt", db_update_receipt)

    graph_builder.add_edge(START, "get_from_db")
    graph_builder.add_edge("get_from_db", "ask_need_change")
    graph_builder.add_conditional_edges(
        "ask_need_change",
        route,
        {
            True: "db_update_receipt",
            False: END,
        }
    )
    graph_builder.add_edge("db_update_receipt", END)

    graph = graph_builder.compile()

    return graph
