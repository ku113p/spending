from .agents import agents, calls, schema

async def to_receipt(text: str) -> calls.AgentResponse:
    return await calls.ask_agent(
        agents.receipt_extractor,
        output_schema=schema.Receipt,
        question=text
    )
