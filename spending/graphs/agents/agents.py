from dataclasses import dataclass
from . import schemas

@dataclass
class Agent:
    model: str
    system_prompt: str
    response_format: type


receipt_extractor = Agent(
    model="gpt-4.1-nano",
    response_format=schemas.Receipt,
    system_prompt="""
Extract structured receipt data from noisy OCR-like text.

Rules:
- Match each product with the price that appears directly below or beside it.
- Preserve the original order of products.
- If the same product appears multiple times, include each occurrence.
- If the date is invalid, missing, or ambiguous, return the fallback date"
- Never guess or fabricate data. If a field is missing or unreadable — leave it fallback.
"""
)


products_n_shop_normalizer = Agent(
    model="gpt-4.1",
    response_format=schemas.NormalizedOutput,
    system_prompt="""
Normalize product names and the shop name extracted from OCR-like receipt text.

Instructions:
- Convert raw or abbreviated product names into clean, human-readable names.
  Example: "LPTN" → "Lipton", "BRD" → "Bread", "AMZNLK" → "Amazon Milk"
- Use common sense and known brand references when decoding abbreviations or OCR errors.
- Only normalize when you're reasonably confident. If uncertain — return the raw name.
- Categorize each product appropriately. (e.g., "Beverage", "Dairy", "Bakery")
- Normalize the shop name (e.g., "7 ELEVEN PH" → "7-Eleven")
- Do not invent data. If a value is unreadable or unknown — return as-is or leave empty.
"""
)


correct_receipt = Agent(
    model="gpt-4.1-mini",
    response_format=schemas.CorrectReceiptRequest,
    system_prompt="""
Update receipt information based strictly on the user's instructions.

Rules:
- Only update the fields that the user has explicitly asked to change.
- Never modify the total, date, or any unrelated data unless the user directly requests it.
- Do not recalculate or "fix" values unless told to.
- Preserve the rest of the receipt exactly as it was. Do not remove or reorder items.
- Your role is to apply surgical corrections, not to improve or re-interpret the data.
"""
)
