from dataclasses import dataclass
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from . import agents


@dataclass
class AgentResponse:
    raw: AIMessage
    parsed: BaseModel | None
    parsing_error: Exception | None
    

async def ask_agent(agent: agents.Agent, output_schema: BaseModel, question: str) -> AgentResponse:
    llm = ChatOpenAI(model=agent.model).with_structured_output(output_schema, include_raw=True)

    messages = [
        SystemMessage(content=agent.system_prompt),
        HumanMessage(content=question),
    ]

    response = await llm.ainvoke(messages)

    return AgentResponse(**response)
