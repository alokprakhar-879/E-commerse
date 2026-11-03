from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Inventory, Product, Category
from backend.schemas import InventoryResponse, InventoryUpdate, LowStockItem

router = APIRouter(prefix="/inventory", tags=["Inventory"])

@router.get("", response_model=List[InventoryResponse])
def get_all_inventory(db: Session = Depends(get_db)):
    """Retrieve all inventory records."""
    return db.query(Inventory).order_by(Inventory.product_id).all()

@router.get("/low-stock", response_model=List[LowStockItem])
def get_low_stock_items(db: Session = Depends(get_db)):
    """
    DBMS Query: Alert on products where available quantity <= reorder_level threshold.
    Performs SQL JOIN across products, inventory, and categories.
    """
    results = (
        db.query(
            Product.id.label("product_id"),
            Product.name.label("name"),
            Product.sku.label("sku"),
            Category.name.label("category_name"),
            Inventory.quantity.label("quantity"),
            Inventory.reorder_level.label("reorder_level"),
            Product.selling_price.label("selling_price")
        )
        .join(Inventory, Product.id == Inventory.product_id)
        .join(Category, Product.category_id == Category.id)
        .filter(Inventory.quantity <= Inventory.reorder_level)
        .order_by(Inventory.quantity.asc())
        .all()
    )

    return [
        LowStockItem(
            product_id=r.product_id,
            name=r.name,
            sku=r.sku,
            category_name=r.category_name,
            quantity=r.quantity,
            reorder_level=r.reorder_level,
            selling_price=r.selling_price
        )
        for r in results
    ]

@router.put("/{product_id}", response_model=InventoryResponse)
def update_inventory_level(
    product_id: int,
    inv_update: InventoryUpdate,
    db: Session = Depends(get_db)
):
    """Update stock quantity or reorder threshold for a specific product."""
    inv = db.query(Inventory).filter(Inventory.product_id == product_id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory record for product id {product_id} not found"
        )

    if inv_update.quantity is not None:
        inv.quantity = inv_update.quantity
    if inv_update.reorder_level is not None:
        inv.reorder_level = inv_update.reorder_level

    db.commit()
    db.refresh(inv)
    return inv
