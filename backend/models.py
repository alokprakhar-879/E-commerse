from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Numeric, Text, DateTime,
    ForeignKey, CheckConstraint, Index, func
)
from sqlalchemy.orm import relationship
from backend.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 1-to-N: Category has many Products
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    name = Column(String(255), nullable=False)
    sku = Column(String(50), nullable=False, unique=True)
    cost_price = Column(Numeric(10, 2), nullable=False)
    selling_price = Column(Numeric(10, 2), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("cost_price > 0", name="chk_products_cost_price"),
        CheckConstraint("selling_price > 0", name="chk_products_selling_price"),
        Index("idx_products_category_id", "category_id"),
    )

    # Relationships
    category = relationship("Category", back_populates="products")
    # 1-to-1 relationship with Inventory
    inventory = relationship("Inventory", back_populates="product", uselist=False, cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product")


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    quantity = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, nullable=False, default=5)
    last_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="chk_inventory_quantity"),
        CheckConstraint("reorder_level >= 0", name="chk_inventory_reorder_level"),
        Index("idx_inventory_product_id", "product_id"),
    )

    product = relationship("Product", back_populates="inventory")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 1-to-N: Customer has many Orders
    orders = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(
        Integer,
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    order_status = Column(
        String(20),
        nullable=False,
        default="PENDING"
    )
    total_amount = Column(Numeric(12, 2), nullable=False, default=0.00)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    __table_args__ = (
        CheckConstraint(
            "order_status IN ('PENDING', 'PAID', 'CANCELLED')",
            name="chk_orders_status"
        ),
        CheckConstraint("total_amount >= 0", name="chk_orders_total_amount"),
        Index("idx_orders_customer_id", "customer_id"),
        Index("idx_orders_created_at", "created_at"),
    )

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_order_items_quantity"),
        CheckConstraint("unit_price > 0", name="chk_order_items_unit_price"),
        CheckConstraint("subtotal > 0", name="chk_order_items_subtotal"),
        Index("idx_order_items_order_id", "order_id"),
        Index("idx_order_items_product_id", "product_id"),
    )

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    payment_status = Column(
        String(20),
        nullable=False,
        default="SUCCESS"
    )
    payment_method = Column(String(50), nullable=False, default="CREDIT_CARD")
    amount = Column(Numeric(12, 2), nullable=False)
    transaction_id = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "payment_status IN ('SUCCESS', 'FAILED', 'REFUNDED')",
            name="chk_payments_status"
        ),
        CheckConstraint("amount > 0", name="chk_payments_amount"),
        Index("idx_payments_order_id", "order_id"),
    )

    order = relationship("Order", back_populates="payments")
