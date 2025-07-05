from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class ProductCategoryEnum(str, Enum):
    FUN_ALLOWANCE = "Fun Allowance"
    FOOD = "Food"
    SHOPPING = "Shopping"
    BILLS = "Bills"
    GROCERIES = "Groceries"
    TRANSPORTATION = "Transportation"
    OTHERS = "Others"


class ShopCategoryEnum(str, Enum):
    FOOD_AND_DRINK = "Food & Drink"
    CLOTHING_AND_ACCESSORIES = "Clothing & Accessories"
    HEALTH_AND_BEAUTY = "Health & Beauty"
    HOME_AND_LIVING = "Home & Living"
    ELECTRONICS = "Electronics"
    ENTERTAINMENT = "Entertainment"
    SPORTS_AND_OUTDOORS = "Sports & Outdoors"
    OTHER = "Other"


class Name(BaseModel):
    raw: str = Field(
        description="The original, unprocessed name or label text (e.g., from OCR or source text)."
    )
    normalized: Optional[str] = Field(
        default=None,
        description="Corrected and cleaned name, if normalization is possible."
    )


class Product(BaseModel):
    name: Name = Field(
        description="Product name as both raw and optionally normalized values."
    )
    price: float = Field(
        description="Price of the product."
    )
    category: ProductCategoryEnum = Field(
        description="High-level category assigned to this product."
    )


class Shop(BaseModel):
    name: Name = Field(
        description="Shop name in both raw and normalized form."
    )
    category: ShopCategoryEnum = Field(
        description="Shop classification based on type or domain."
    )


class Receipt(BaseModel):
    number: str = Field(
        description="Receipt or invoice number, or another unique identifier."
    )
    created_at: datetime = Field(
        description="Datetime of receipt issuance."
    )
    shop: Shop = Field(
        description="Metadata about the shop where the purchase occurred."
    )
    products: List[Product] = Field(
        description="List of purchased products."
    )
