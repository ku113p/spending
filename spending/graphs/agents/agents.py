from dataclasses import dataclass

from . import schemas


@dataclass
class Agent:
    model: str
    system_prompt: str
    response_format: schemas.Receipt


receipt_extractor = Agent(
    model="gpt-4.1-nano",
    response_format=schemas.Receipt,
    system_prompt="""Extract structured receipt data from noisy text (e.g. OCR). If possible create corrected name.
Match each item with the price that appears directly below it and preserve the item order from the text.""",
)

products_n_shop_normalizer = Agent(
    model="gpt-4.1",
    response_format=schemas.NormalizedOutput,
    system_prompt="Normalize and categorize the product names and shop name from noisy or OCR text.",
)
