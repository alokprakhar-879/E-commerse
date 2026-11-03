from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

from backend.database import get_db
from backend.models import Order, OrderItem, Product, Category
from backend.schemas import (
    DailySalesReportItem,
    ProfitReportResponse,
    ProductProfitReportItem,
    CategoryProfitReportItem,
    TopProductReportItem
)

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/sales", response_model=List[DailySalesReportItem])
def get_daily_sales(
    from_date: Optional[str] = Query(None, alias="from", description="YYYY-MM-DD start date"),
    to_date: Optional[str] = Query(None, alias="to", description="YYYY-MM-DD end date"),
    db: Session = Depends(get_db)
):
    """
    SQL JOIN / GROUP BY / SUM query for Daily Sales (PAID orders only).
    Formats date strings and totals cleanly for Chart.js line charts.
    """
    date_col = cast(Order.created_at, Date)
    query = (
        db.query(
            date_col.label("sale_date"),
            func.sum(Order.total_amount).label("total_sales"),
            func.count(Order.id).label("order_count")
        )
        .filter(Order.order_status == "PAID")
    )

    if from_date:
        query = query.filter(date_col >= from_date)
    if to_date:
        query = query.filter(date_col <= to_date)

    results = (
        query.group_by(date_col)
        .order_by(date_col.asc())
        .all()
    )

    report = []
    for r in results:
        sale_dt = r.sale_date.strftime("%Y-%m-%d") if isinstance(r.sale_date, (date, datetime)) else str(r.sale_date)
        report.append(
            DailySalesReportItem(
                date=sale_dt,
                total_sales=r.total_sales or Decimal("0.00"),
                order_count=r.order_count or 0
            )
        )
    return report


@router.get("/profit", response_model=ProfitReportResponse)
def get_profit_report(db: Session = Depends(get_db)):
    """
    Calculates profit and margins per Product and per Category.
    Formula: Profit = Revenue (selling_price * qty) - Cost (cost_price * qty).
    Restricted to PAID orders only.
    """
    # 1. Profit by Product
    prod_results = (
        db.query(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Category.name.label("category_name"),
            func.sum(OrderItem.quantity).label("units_sold"),
            func.sum(OrderItem.subtotal).label("revenue"),
            func.sum(OrderItem.quantity * Product.cost_price).label("total_cost")
        )
        .join(OrderItem, Product.id == OrderItem.product_id)
        .join(Order, OrderItem.order_id == Order.id)
        .join(Category, Product.category_id == Category.id)
        .filter(Order.order_status == "PAID")
        .group_by(Product.id, Product.name, Category.name)
        .order_by(func.sum(OrderItem.subtotal - (OrderItem.quantity * Product.cost_price)).desc())
        .all()
    )

    by_product = []
    for r in prod_results:
        rev = r.revenue or Decimal("0.00")
        cost = r.total_cost or Decimal("0.00")
        profit = rev - cost
        margin = float((profit / rev) * 100) if rev > 0 else 0.0
        by_product.append(
            ProductProfitReportItem(
                product_id=r.product_id,
                product_name=r.product_name,
                category_name=r.category_name,
                units_sold=r.units_sold or 0,
                revenue=rev,
                total_cost=cost,
                profit=profit,
                margin_percent=round(margin, 2)
            )
        )

    # 2. Profit by Category
    cat_results = (
        db.query(
            Category.id.label("category_id"),
            Category.name.label("category_name"),
            func.sum(OrderItem.quantity).label("units_sold"),
            func.sum(OrderItem.subtotal).label("revenue"),
            func.sum(OrderItem.quantity * Product.cost_price).label("total_cost")
        )
        .join(Product, Category.id == Product.category_id)
        .join(OrderItem, Product.id == OrderItem.product_id)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Order.order_status == "PAID")
        .group_by(Category.id, Category.name)
        .order_by(func.sum(OrderItem.subtotal - (OrderItem.quantity * Product.cost_price)).desc())
        .all()
    )

    by_category = []
    for r in cat_results:
        rev = r.revenue or Decimal("0.00")
        cost = r.total_cost or Decimal("0.00")
        profit = rev - cost
        by_category.append(
            CategoryProfitReportItem(
                category_id=r.category_id,
                category_name=r.category_name,
                units_sold=r.units_sold or 0,
                revenue=rev,
                total_cost=cost,
                profit=profit
            )
        )

    return ProfitReportResponse(by_product=by_product, by_category=by_category)


@router.get("/top-products", response_model=List[TopProductReportItem])
def get_top_products(
    limit: int = Query(5, ge=1, le=20, description="Top N products by revenue"),
    db: Session = Depends(get_db)
):
    """
    Top N products ranked by total revenue from confirmed PAID orders.
    Uses SQL GROUP BY and SUM with descending ordering.
    """
    results = (
        db.query(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.sku.label("product_sku"),
            func.sum(OrderItem.quantity).label("total_units_sold"),
            func.sum(OrderItem.subtotal).label("total_revenue")
        )
        .join(OrderItem, Product.id == OrderItem.product_id)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Order.order_status == "PAID")
        .group_by(Product.id, Product.name, Product.sku)
        .order_by(func.sum(OrderItem.subtotal).desc())
        .limit(limit)
        .all()
    )

    return [
        TopProductReportItem(
            product_id=r.product_id,
            name=r.product_name,
            sku=r.product_sku,
            total_units_sold=r.total_units_sold or 0,
            total_revenue=r.total_revenue or Decimal("0.00")
        )
        for r in results
    ]
