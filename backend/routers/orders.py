import uuid
import threading
from typing import List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, text

from backend.database import get_db
from backend.models import Order, OrderItem, Inventory, Product, Customer, Payment
from backend.schemas import (
    OrderCreate, OrderResponse, OrderItemResponse, PaymentResponse
)

# Concurrency lock for SQLite fallback dialect (since SQLite lacks row-level FOR UPDATE)
_sqlite_mutex = threading.Lock()

router = APIRouter(prefix="/orders", tags=["Orders"])

def _format_order(order: Order) -> OrderResponse:
    items_out = []
    for it in order.items:
        items_out.append(
            OrderItemResponse(
                id=it.id,
                product_id=it.product_id,
                product_name=it.product.name if it.product else None,
                product_sku=it.product.sku if it.product else None,
                quantity=it.quantity,
                unit_price=it.unit_price,
                subtotal=it.subtotal
            )
        )
    payments_out = []
    for pay in order.payments:
        payments_out.append(
            PaymentResponse(
                id=pay.id,
                order_id=pay.order_id,
                payment_status=pay.payment_status,
                payment_method=pay.payment_method,
                amount=pay.amount,
                transaction_id=pay.transaction_id,
                created_at=pay.created_at
            )
        )
    return OrderResponse(
        id=order.id,
        customer_id=order.customer_id,
        customer_name=order.customer.name if order.customer else None,
        customer_email=order.customer.email if order.customer else None,
        order_status=order.order_status,
        total_amount=order.total_amount,
        created_at=order.created_at,
        items=items_out,
        payments=payments_out
    )

@router.get("", response_model=List[OrderResponse])
def get_orders(db: Session = Depends(get_db)):
    """Retrieve all orders with items and customer details."""
    orders = db.query(Order).order_by(Order.id.desc()).all()
    return [_format_order(o) for o in orders]

@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Retrieve a single order by ID."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found"
        )
    return _format_order(order)

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def place_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    """
    Core DBMS Feature: Place an order in ONE atomic ACID transaction.
    
    ACID Guarantees & Concurrency Control:
    1. CONCURRENCY CONTROL (Deadlock Prevention):
       - Sort product IDs in ascending order before acquiring locks.
       - If two concurrent transactions need items (e.g., A & B), both will acquire
         locks in the same deterministic sequence (A then B), making circular wait deadlocks impossible.
    2. ISOLATION & PESSIMISTIC LOCKING:
       - Uses `SELECT ... FOR UPDATE` (via SQLAlchemy's `.with_for_update()`).
       - Obtains exclusive row-level locks on the inventory rows.
       - Concurrent transactions attempting to modify the same inventory must wait
         until this transaction commits or rolls back, completely eliminating race conditions
         and lost updates under high concurrency.
    3. ATOMICITY:
       - Either the entire operation succeeds (Inventory decremented, Order placed,
         OrderItems recorded, Payment logged, Status='PAID'), or if anything fails
         (insufficient stock or simulated payment failure), the entire transaction rolls back (`db.rollback()`).
    4. CONSISTENCY:
       - Database check constraints (`quantity >= 0`, `selling_price > 0`, `status IN (...)`)
         are rigorously maintained.
    """
    # 0. Validate Customer
    customer = db.query(Customer).filter(Customer.id == order_in.customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with id {order_in.customer_id} does not exist"
        )

    # Consolidate duplicate products in the same order payload if any
    consolidated_items = {}
    for item in order_in.items:
        consolidated_items[item.product_id] = consolidated_items.get(item.product_id, 0) + item.quantity

    # a) DEADLOCK PREVENTION: Sort by product_id in ascending order
    sorted_product_ids = sorted(consolidated_items.keys())

    is_sqlite = (db.bind.dialect.name == "sqlite") if db.bind else False
    if is_sqlite:
        _sqlite_mutex.acquire()

    try:
        locked_inventories = {}
        products_map = {}

        # a) PESSIMISTIC LOCKING: Acquire SELECT ... FOR UPDATE locks in sorted order
        for pid in sorted_product_ids:
            inv = db.query(Inventory).filter(
                Inventory.product_id == pid
            ).with_for_update().first()

            if not inv:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Inventory record for product id {pid} not found"
                )

            prod = db.query(Product).filter(Product.id == pid).first()
            if not prod:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {pid} not found"
                )

            locked_inventories[pid] = inv
            products_map[pid] = prod

        # b) STOCK CHECK & ATOMIC ROLLBACK ON INSUFFICIENT INVENTORY
        for pid, requested_qty in consolidated_items.items():
            inv = locked_inventories[pid]
            prod = products_map[pid]
            if inv.quantity < requested_qty:
                # ATOMICITY: Abort transaction and rollback all row locks
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Insufficient stock for '{prod.name}' (SKU: {prod.sku}). Available: {inv.quantity}, Requested: {requested_qty}"
                )

        # c) INSERT ORDERS AND ORDER_ITEMS, COMPUTE TOTAL, DECREMENT INVENTORY
        total_amount = Decimal("0.00")
        order = Order(
            customer_id=order_in.customer_id,
            order_status="PENDING",
            total_amount=Decimal("0.00")
        )
        db.add(order)
        db.flush()  # Generates order.id for foreign keys

        for pid, requested_qty in consolidated_items.items():
            prod = products_map[pid]
            inv = locked_inventories[pid]

            subtotal = prod.selling_price * requested_qty
            total_amount += subtotal

            # Decrement inventory quantity safely under exclusive row lock
            inv.quantity -= requested_qty

            order_item = OrderItem(
                order_id=order.id,
                product_id=pid,
                quantity=requested_qty,
                unit_price=prod.selling_price,
                subtotal=subtotal
            )
            db.add(order_item)

        order.total_amount = total_amount

        # d) INSERT PAYMENTS ROW & SIMULATE SUCCESS / FAILURE
        # If simulation flag is set, demonstrate transaction atomicity rollback
        if order_in.simulate_payment_failure:
            # ATOMICITY: Simulated failure rolls back decremented inventory & order
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Payment gateway simulated failure: Transaction rolled back, stock restored."
            )

        # e) PAYMENT SUCCESS SETS ORDER STATUS TO PAID
        payment = Payment(
            order_id=order.id,
            payment_status="SUCCESS",
            payment_method=order_in.payment_method,
            amount=total_amount,
            transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}"
        )
        db.add(payment)
        order.order_status = "PAID"

        # Commit all state changes atomically
        db.commit()
        db.refresh(order)
        return _format_order(order)

    except HTTPException:
        # Re-raise already structured HTTP exceptions (e.g. 404, 409, 422)
        db.rollback()
        raise
    except Exception as exc:
        # Unexpected error rolls back full transaction
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transaction failed: {str(exc)}"
        )
    finally:
        if is_sqlite:
            _sqlite_mutex.release()


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    """
    Cancel an existing order in ONE atomic ACID transaction:
    1. Lock order and items to prevent concurrent modifications.
    2. Check status (cannot cancel already cancelled orders).
    3. Restore inventory quantity for each purchased item.
    4. Set Order status to CANCELLED.
    5. Mark associated Payment as REFUNDED.
    """
    try:
        # Lock order row
        order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if not order:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with id {order_id} not found"
            )

        if order.order_status == "CANCELLED":
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order is already cancelled"
            )

        # Restore inventory for all items in sorted order
        sorted_items = sorted(order.items, key=lambda x: x.product_id)
        for item in sorted_items:
            inv = db.query(Inventory).filter(
                Inventory.product_id == item.product_id
            ).with_for_update().first()
            if inv:
                inv.quantity += item.quantity

        order.order_status = "CANCELLED"

        # Update payment status to REFUNDED
        for payment in order.payments:
            if payment.payment_status == "SUCCESS":
                payment.payment_status = "REFUNDED"

        db.commit()
        db.refresh(order)
        return _format_order(order)

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel order: {str(exc)}"
        )
