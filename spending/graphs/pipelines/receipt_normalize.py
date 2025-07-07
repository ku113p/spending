from typing import TypedDict

from langgraph.graph import START, END, StateGraph
from langchain_core.runnables import Runnable

from graphs.agents import agents, calls, schemas


class State(TypedDict):
    receipt: schemas.Receipt
    normalize_output: schemas.NormalizedOutput
    normalized_receipt: schemas.NormalizedReceipt


async def receipt_to_normalize_items(state: State):
    parsed = await calls.ask_agent_question(
        agents.products_n_shop_normalizer,
        question=state['receipt'].as_normalize_input.model_dump_json()
    )

    return {"normalize_output": parsed}


async def to_normalized_receipt(state: State):
    normalized_receipt = schemas.NormalizedReceipt.from_receipt_and_output(
        receipt=state['receipt'],
        normalized=state['normalize_output'],
    )

    return {"normalized_receipt": normalized_receipt}


def create() -> Runnable:
    graph_builder = StateGraph(State)

    graph_builder.add_node("receipt_to_normalize_items", receipt_to_normalize_items)
    graph_builder.add_node("to_normalized_receipt", to_normalized_receipt)

    graph_builder.add_edge(START, "receipt_to_normalize_items")
    graph_builder.add_edge("receipt_to_normalize_items", "to_normalized_receipt")
    graph_builder.add_edge("to_normalized_receipt", END)

    graph = graph_builder.compile()

    return graph
