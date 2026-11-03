from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.database import get_db
from backend.models import Product, Inventory, Category, OrderItem
from backend.schemas import ProductCreate, ProductUpdate, ProductResponse, InventoryResponse

router = APIRouter(prefix="/products", tags=["Products"])

def _format_product_response(p: Product) -> ProductResponse:
    inv = None
    if p.inventory:
        inv = InventoryResponse(
            id=p.inventory.id,
            product_id=p.inventory.product_id,
            quantity=p.inventory.quantity,
            reorder_level=p.inventory.reorder_level,
            last_updated=p.inventory.last_updated
        )
    return ProductResponse(
        id=p.id,
        category_id=p.category_id,
        name=p.name,
        sku=p.sku,
        cost_price=p.cost_price,
        selling_price=p.selling_price,
        description=p.description,
        created_at=p.created_at,
        category_name=p.category.name if p.category else None,
        inventory=inv
    )

@router.get("", response_model=List[ProductResponse])
def get_products(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    search: Optional[str] = Query(None, description="Search by product name or SKU"),
    db: Session = Depends(get_db)
):
    """
    List products with optional category filtering and keyword search.
    Supports 3NF relationships by joining Category and Inventory.
    """
    query = db.query(Product)

    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Product.name.ilike(search_term),
                Product.sku.ilike(search_term)
            )
        )

    products = query.order_by(Product.id).all()
    return [_format_product_response(p) for p in products]

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Retrieve product details by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    return _format_product_response(product)

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    """
    Create a new Product and its 1-1 Inventory entry in a SINGLE atomic transaction.
    If SKU is duplicate or Category does not exist, transaction safely aborts.
    """
    # 1. Validate Category FK existence
    category = db.query(Category).filter(Category.id == product_in.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {product_in.category_id} does not exist"
        )

    # 2. Check SKU uniqueness
    existing_sku = db.query(Product).filter(Product.sku.ilike(product_in.sku.strip())).first()
    if existing_sku:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with SKU '{product_in.sku}' already exists"
        )

    try:
        # ATOMICITY: Product and 1-1 Inventory created together
        product = Product(
            category_id=product_in.category_id,
            name=product_in.name.strip(),
            sku=product_in.sku.strip().upper(),
            cost_price=product_in.cost_price,
            selling_price=product_in.selling_price,
            description=product_in.description
        )
        db.add(product)
        db.flush()  # Flush to populate product.id for foreign key relationship

        inventory = Inventory(
            product_id=product.id,
            quantity=product_in.initial_quantity,
            reorder_level=product_in.reorder_level
        )
        db.add(inventory)
        db.commit()
        db.refresh(product)
        return _format_product_response(product)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to create product: {str(e)}"
        )

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_in: ProductUpdate, db: Session = Depends(get_db)):
    """Update product details and/or inventory quantities."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )

    if product_in.category_id is not None:
        cat = db.query(Category).filter(Category.id == product_in.category_id).first()
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {product_in.category_id} does not exist"
            )
        product.category_id = product_in.category_id

    if product_in.sku is not None:
        sku_check = db.query(Product).filter(
            Product.sku.ilike(product_in.sku.strip()),
            Product.id != product_id
        ).first()
        if sku_check:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product with SKU '{product_in.sku}' already exists"
            )
        product.sku = product_in.sku.strip().upper()

    if product_in.name is not None:
        product.name = product_in.name.strip()
    if product_in.cost_price is not None:
        product.cost_price = product_in.cost_price
    if product_in.selling_price is not None:
        product.selling_price = product_in.selling_price
    if product_in.description is not None:
        product.description = product_in.description

    # Update 1-1 Inventory if provided
    if product_in.quantity is not None or product_in.reorder_level is not None:
        if not product.inventory:
            product.inventory = Inventory(product_id=product.id, quantity=0, reorder_level=5)
        if product_in.quantity is not None:
            product.inventory.quantity = product_in.quantity
        if product_in.reorder_level is not None:
            product.inventory.reorder_level = product_in.reorder_level

    db.commit()
    db.refresh(product)
    return _format_product_response(product)

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete a product if it hasn't been referenced in existing orders."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )

    # Check for order item references
    has_orders = db.query(OrderItem).filter(OrderItem.product_id == product_id).first()
    if has_orders:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete product because it has associated order records"
        )

    db.delete(product)
    db.commit()
