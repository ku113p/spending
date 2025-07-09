from typing import TypedDict

from langgraph.graph import START, END, StateGraph
from langchain_core.runnables import Runnable

from graphs.agents import agents, calls, schemas
from graphs.pipelines.utils import one_graph_decorator
from integrations.to_text import ToTextStrategy


class State(TypedDict):
    image_fp: str
    image_text: str
    receipt: schemas.Receipt


async def image_to_text(state: State):
    text = await ToTextStrategy.MICROSERVICE.to_text(state["image_fp"])
    return {"image_text": text}


async def text_to_receipt(state: State):
    parsed = await calls.ask_agent_question(
        agents.receipt_extractor,
        question=state["image_text"]
    )

    return {"receipt": parsed}


@one_graph_decorator
def create() -> Runnable:
    graph_builder = StateGraph(State)

    graph_builder.add_node("image_to_text", image_to_text)
    graph_builder.add_node("text_to_receipt", text_to_receipt)

    graph_builder.add_edge(START, "image_to_text")
    graph_builder.add_edge("image_to_text", "text_to_receipt")
    graph_builder.add_edge("text_to_receipt", END)

    graph = graph_builder.compile()

    return graph