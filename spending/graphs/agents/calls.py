from dataclasses import dataclass
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

import utils
from . import agents

logger = utils.create_logger(__name__)


@dataclass
class Metadata:
    id: str
    tokens: dict


@dataclass
class AgentResponse:
    raw: AIMessage
    parsed: BaseModel | None
    parsing_error: Exception | None
    
    @property
    def metadata(self) -> Metadata:
        req_id, tokens = self.raw.id, self.raw.usage_metadata
        return Metadata(id=req_id, tokens=tokens)


async def ask_agent_question(agent: agents.Agent, output_schema: BaseModel, question: str) -> BaseModel:
    return await ask_agent(agent, output_schema, [HumanMessage(content=question)])


async def ask_agent(agent: agents.Agent, output_schema: BaseModel, messages: list[BaseMessage]) -> BaseModel:
    llm = ChatOpenAI(model=agent.model).with_structured_output(output_schema, include_raw=True)

    messages = [SystemMessage(content=agent.system_prompt), *messages]

    response = await llm.ainvoke(messages)
    agent_response = AgentResponse(**response)

    logger.debug(f"raw response metadata: {agent_response.metadata}")

    return agent_response.parsed
