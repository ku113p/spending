from dataclasses import dataclass
from . import schemas

@dataclass
class Agent:
    model: str
    system_prompt: str
    response_format: type


receipt_extractor = Agent(
    model="gpt-5-nano",
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
    model="gpt-5",
    response_format=schemas.NormalizedOutput,
    system_prompt="""
Normalize product names and the shop name extracted from OCR-like receipt text.

Instructions:
- Convert raw or abbreviated product names into clean, human-readable names.
  Example: "LPTN" → "Lipton", "BRD" → "Bread", "AMZNLK" → "Amazon Milk"
- Use known brands and contextual clues to correct OCR mistakes.

Examples:
- Product: "CHKN RICE MEAL" → "Chicken Rice Meal", Category: Food
- Product: "COKE 500ML" → "Coca-Cola 500ml", Category: Beverage
- Product: "LAYS CHS" → "Lay's Cheese Chips", Category: Junk Food
- Shop: "7 ELEVEN PH" → "7-Eleven", Category: Convenience Store
- Shop: "HOP INN HOTEL" → "Hop Inn Hotel", Category: Hotel

Notes:
- Do not invent missing data. Leave values unchanged if unsure.
- Prefer literal matching and known brands; do not guess unfamiliar terms.
"""
)


correct_receipt = Agent(
    model="gpt-5-mini",
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
