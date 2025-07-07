from typing import TypedDict

from langgraph.graph import START, END, StateGraph
from langchain_core.runnables import Runnable

from graphs.agents import schemas
from graphs.pipelines import receipt_normalize
from graphs.pipelines.photo_to_receipt import openai_only

class State(TypedDict):
    image_fp: str
    receipt: schemas.Receipt
    normalized_receipt: schemas.NormalizedReceipt


def create() -> Runnable:
    graph_builder = StateGraph(State)

    graph_builder.add_node("node_photo_to_receipt", openai_only.create())
    graph_builder.add_node("node_receipt_normalize", receipt_normalize.create())

    graph_builder.add_edge(START, "node_photo_to_receipt")
    graph_builder.add_edge("node_photo_to_receipt", "node_receipt_normalize")
    graph_builder.add_edge("node_receipt_normalize", END)

    graph = graph_builder.compile()

    return graph
