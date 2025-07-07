import base64
from typing import TypedDict

from langgraph.graph import START, END, StateGraph
from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable

from graphs.agents import agents, calls, schemas
from graphs.pipelines.utils import one_graph_decorator


class State(TypedDict):
    image_fp: str
    receipt: schemas.Receipt


async def image_to_receipt(state: State):
    with open(state["image_fp"], "rb") as img:
        img = base64.b64encode(img.read()).decode()

    messages = [
        HumanMessage(content=[
            {"type": "text", "text": "Describe the image below."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}},
        ])
    ]

    parsed = await calls.ask_agent(
        agent=agents.receipt_extractor,
        messages=messages,
    )

    return {"receipt": parsed}


@one_graph_decorator
def create() -> Runnable:
    graph_builder = StateGraph(State)

    graph_builder.add_node("image_to_receipt", image_to_receipt)

    # TODO minimize image
    graph_builder.add_edge(START, "image_to_receipt")
    graph_builder.add_edge("image_to_receipt", END)

    graph = graph_builder.compile()

    return graph
