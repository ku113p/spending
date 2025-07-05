from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


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
    raw: Optional[str]    # Raw OCR'd product name (may contain errors)
    normalized: str  # Cleaned/inferred product name


class Product(BaseModel):
    name: Name
    price_per_unit: float
    category: ProductCategoryEnum
    amount: int = 1


class Shop(BaseModel):
    name: Name
    category: ShopCategoryEnum


class Receipt(BaseModel):
    number: str
    created_at: datetime
    shop: Shop
    products: list[Product]
