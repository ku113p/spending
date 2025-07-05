from dataclasses import dataclass

from . import schema


@dataclass
class Agent:
    model: str
    system_prompt: str
    response_format: schema.Receipt


receipt_extractor = Agent(
    model="gpt-4.1",
    response_format=schema.Receipt,
    system_prompt="""Extract structured receipt data from noisy text (e.g. OCR). If possible create corrected name.
Match each item with the price that appears directly below it and preserve the item order from the text.""",
)
