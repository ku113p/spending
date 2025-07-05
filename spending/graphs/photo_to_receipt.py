from typing import TypedDict

from langgraph.graph import START, END, StateGraph
from langchain_core.runnables import Runnable

from graphs.agents import agents, calls, schema
from to_text.to_text import ToTextStrategy


class State(TypedDict):
    image_fp: str
    image_text: str
    receipt: calls.AgentResponse


async def image_to_text(state: State):
    text = await ToTextStrategy.MICROSERVICE.to_text(state["image_fp"])
    return {"image_text": text}


async def text_to_receipt(state: State) -> calls.AgentResponse:
    agent_response = await calls.ask_agent(
        agents.receipt_extractor,
        output_schema=schema.Receipt,
        question=state["image_text"]
    )

    return {"receipt": agent_response}


def get_graph() -> Runnable:
    def create():
        graph_builder = StateGraph(State)

        graph_builder.add_node("image_to_text", image_to_text)
        graph_builder.add_node("text_to_receipt", text_to_receipt)

        graph_builder.add_edge(START, "image_to_text")
        graph_builder.add_edge("image_to_text", "text_to_receipt")
        graph_builder.add_edge("text_to_receipt", END)

        graph = graph_builder.compile()

        return graph
    
    if not hasattr(create, "instance"):
        setattr(create, "instance", create())
    
    return getattr(create, "instance")
