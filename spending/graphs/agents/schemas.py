from datetime import datetime
from enum import Enum
from typing import Optional, Self
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
    created_at: datetime = Field(description="iso format datetime string")
    shop: Shop
    staff_name: Optional[str] = None
    products: list[Product]
    total: float = Field(description="Total amount before payment")
    payment: Payment
    tax: Optional[Tax] = None
    number: str = Field(description="Invoice or receipt number.")

    @property
    def as_normalize_input(self) -> "NormalizeInput":
        return NormalizeInput(
            product_names=[p.name for p in self.products],
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


class NamePair(BaseModel):
    raw: str = Field(description="Original prodcut name")
    normalized: str = Field(description="Normalized product name")


class NormalizedProduct(BaseModel):
    name: NamePair
    category: ProductCategoryEnum = Field(description="Predicted product category")


class NormalizedShop(BaseModel):
    name: NamePair
    category: ShopCategoryEnum = Field(description="Predicted shop category")


class NormalizedOutput(BaseModel):
    products: list[NormalizedProduct] = Field(description="List of normalized products with categories")
    shop: NormalizedShop = Field(description="Normalized shop with category")


class NormalizedReceiptProduct(BaseModel):
    name: NamePair
    category: ProductCategoryEnum
    price: float


class NormalizedReceiptShop(BaseModel):
    name: NamePair
    category: ShopCategoryEnum
    address: Optional[str] = None


class NormalizedReceipt(BaseModel):
    created_at: datetime = Field(description="iso format datetime string")
    shop: NormalizedReceiptShop
    staff_name: Optional[str] = None
    products: list[NormalizedReceiptProduct]
    total: float
    payment: Payment
    tax: Optional[Tax] = None
    number: str

    @classmethod
    def from_raw_mongo(cls, db_object: dict) -> Self:
        return cls.model_validate(db_object["receipt"])

    @classmethod
    def from_receipt_and_output(cls, receipt: Receipt, normalized: NormalizedOutput) -> "NormalizedReceipt":
        norm_products_map: dict[str, NormalizedProduct] = {
            product.name.raw: product
            for product in normalized.products
        }
        products = []
        for rec_product in receipt.products:
            norm_product: NormalizedProduct = norm_products_map[rec_product.name]
            norm_rec_product = NormalizedReceiptProduct(
                name=norm_product.name,
                category=norm_product.category,
                price=rec_product.price,
            )
            products.append(norm_rec_product)

        shop = NormalizedReceiptShop(
            name=normalized.shop.name,
            category=normalized.shop.category,
            address=receipt.shop.address
        )

        return cls(
            created_at=receipt.created_at,
            shop=shop,
            staff_name=receipt.staff_name,
            products=products,
            total=receipt.total,
            payment=receipt.payment,
            tax=receipt.tax,
            number=receipt.number
        )


class ReceiptBase(BaseModel):
    created_at: datetime = Field(description="iso format datetime string")
    shop: NormalizedReceiptShop
    products: list[NormalizedReceiptProduct]
    total: float

    @classmethod
    def from_normalized(cls, norm: NormalizedReceipt) -> Self:
        return cls(
            created_at=norm.created_at,
            shop=norm.shop,
            products=norm.products,
            total=norm.total,
        )


class CorrectReceiptRequest(BaseModel):
    need_change: bool = Field(description="Whether the user wants to change the receipt information.")
    receipt_base: Optional[ReceiptBase] = Field(description="Updated receipt information if the user wants to change it.")
