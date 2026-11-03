from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field, EmailStr, ConfigDict


# ---------------------------------------------------------------------------
# Category Schemas
# ---------------------------------------------------------------------------
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None

class CategoryResponse(CategoryBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Inventory Schemas
# ---------------------------------------------------------------------------
class InventoryBase(BaseModel):
    quantity: int = Field(..., ge=0)
    reorder_level: int = Field(5, ge=0)

class InventoryUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=0)
    reorder_level: Optional[int] = Field(None, ge=0)

class InventoryResponse(InventoryBase):
    id: int
    product_id: int
    last_updated: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Product Schemas
# ---------------------------------------------------------------------------
class ProductBase(BaseModel):
    category_id: int
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=50)
    cost_price: Decimal = Field(..., gt=0)
    selling_price: Decimal = Field(..., gt=0)
    description: Optional[str] = None

class ProductCreate(ProductBase):
    # Creating a product also creates its Inventory row in the same transaction
    initial_quantity: int = Field(0, ge=0)
    reorder_level: int = Field(5, ge=0)

class ProductUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sku: Optional[str] = Field(None, min_length=1, max_length=50)
    cost_price: Optional[Decimal] = Field(None, gt=0)
    selling_price: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=0)
    reorder_level: Optional[int] = Field(None, ge=0)

class ProductResponse(ProductBase):
    id: int
    created_at: Optional[datetime] = None
    inventory: Optional[InventoryResponse] = None
    category_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Customer Schemas
# ---------------------------------------------------------------------------
class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class CustomerResponse(CustomerBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Order & Order Item Schemas
# ---------------------------------------------------------------------------
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)

class PaymentResponse(BaseModel):
    id: int
    order_id: int
    payment_status: str
    payment_method: str
    amount: Decimal
    transaction_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class OrderCreate(BaseModel):
    customer_id: int
    items: List[OrderItemCreate] = Field(..., min_length=1)
    simulate_payment_failure: bool = False
    payment_method: str = "CREDIT_CARD"

class OrderResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    order_status: str
    total_amount: Decimal
    created_at: Optional[datetime] = None
    items: List[OrderItemResponse] = []
    payments: List[PaymentResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Report Schemas
# ---------------------------------------------------------------------------
class DailySalesReportItem(BaseModel):
    date: str
    total_sales: Decimal
    order_count: int

class ProductProfitReportItem(BaseModel):
    product_id: int
    product_name: str
    category_name: str
    units_sold: int
    revenue: Decimal
    total_cost: Decimal
    profit: Decimal
    margin_percent: float

class CategoryProfitReportItem(BaseModel):
    category_id: int
    category_name: str
    units_sold: int
    revenue: Decimal
    total_cost: Decimal
    profit: Decimal

class ProfitReportResponse(BaseModel):
    by_product: List[ProductProfitReportItem]
    by_category: List[CategoryProfitReportItem]

class TopProductReportItem(BaseModel):
    product_id: int
    name: str
    sku: str
    total_units_sold: int
    total_revenue: Decimal

class LowStockItem(BaseModel):
    product_id: int
    name: str
    sku: str
    category_name: str
    quantity: int
    reorder_level: int
    selling_price: Decimal
