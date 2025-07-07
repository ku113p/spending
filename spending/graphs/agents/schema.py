from datetime import datetime
from enum import Enum
from typing import Optional
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


class Product(BaseModel):
    name: str
    price: float  # Unit price; no quantity, no total


class Tax(BaseModel):
    vat: Optional[float] = None       # total VAT amount, if present
    vatable: Optional[float] = None   # total amount subject to VAT
    exempt: Optional[float] = None    # VAT-exempt amount
    zero_rated: Optional[float] = None  # Zero-rated sales
    # Any of these can be None if not available


class Payment(BaseModel):
    method: str            # e.g., "cash", "card", "gcash"
    paid: float            # amount given
    change: Optional[float] = None  # change given, if any


class Shop(BaseModel):
    name: str              # "7-Eleven", "SM Supermarket", etc.
    address: Optional[str] = None


class Receipt(BaseModel):
    created_at: datetime
    shop: Shop
    staff_name: Optional[str] = None
    products: list[Product]
    total: float = Field(description="Total amount before payment")
    payment: Payment
    tax: Optional[Tax] = None
    number: str = Field(description="Invoice or receipt number.")

    def as_normalize_input(self) -> "NormalizeInput":
        return NormalizeInput(
            prodcut_names=[p.name for p in self.products],
            shop=ShopInput(
                name=self.shop.name,
                address=self.shop.address,
            )
        )


class ShopInput(BaseModel):
    name: str = Field(description="Noisy shop name (e.g., from OCR)")
    address: Optional[str] = Field(description="Optional shop address to aid in normalization")


class NormalizeInput(BaseModel):
    product_names: list[str] = Field(description="List of noisy product names")
    shop: ShopInput = Field(description="Shop info including name and optional address")


class NormalizedProduct(BaseModel):
    name: str = Field(description="Normalized product name")
    category: ProductCategoryEnum = Field(description="Predicted product category")


class NormalizedShop(BaseModel):
    name: str = Field(description="Normalized shop name")
    category: ShopCategoryEnum = Field(description="Predicted shop category")


class NormalizedOutput(BaseModel):
    products: list[NormalizedProduct] = Field(description="List of normalized products with categories")
    shop: NormalizedShop = Field(description="Normalized shop with category")
