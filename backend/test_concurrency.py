"""
Concurrency & ACID Race Condition Test Script
Tests pessimistic locking (SELECT ... FOR UPDATE) and transaction atomicity.

Scenario:
A product has exactly 5 units in stock.
20 concurrent threads simultaneously attempt to place an order for 1 unit each.

Expected Outcome:
- Exactly 5 orders succeed (HTTP 201 Created / committed transaction).
- Exactly 15 orders fail with HTTP 409 Conflict ("Insufficient stock").
- Final inventory stock is exactly 0 (Never goes below 0).
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Can also test directly via database session if server is offline
from backend.database import SessionLocal, engine, Base
from backend.models import Product, Inventory, Customer, Order, OrderItem, Payment, Category
from backend.schemas import OrderCreate, OrderItemCreate
from backend.routers.orders import place_order

BASE_URL = "http://localhost:8000"

def setup_concurrency_product_in_db():
    """Sets up a specific test product with exactly 5 units in stock."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Get or create category
        cat = db.query(Category).first()
        if not cat:
            cat = Category(name="Concurrency Test Cat", description="For testing")
            db.add(cat)
            db.flush()

        # Get or create customer
        cust = db.query(Customer).first()
        if not cust:
            cust = Customer(name="Stress Tester", email="stress.tester@test.com")
            db.add(cust)
            db.flush()

        # Find or create test product
        prod = db.query(Product).filter(Product.sku == "TEST-CONC-005").first()
        if not prod:
            prod = Product(
                category_id=cat.id,
                name="Limited Edition Drone",
                sku="TEST-CONC-005",
                cost_price=Decimal("100.00"),
                selling_price=Decimal("150.00"),
                description="Concurrency test item with exactly 5 units"
            )
            db.add(prod)
            db.flush()
            inv = Inventory(product_id=prod.id, quantity=5, reorder_level=2)
            db.add(inv)
        else:
            # Reset stock to exactly 5
            prod.inventory.quantity = 5

        db.commit()
        db.refresh(prod)
        print(f"[Setup] Target Product ID: {prod.id} ('{prod.name}'), Initial Stock: {prod.inventory.quantity}")
        return prod.id, cust.id
    finally:
        db.close()


def run_direct_db_concurrency_test(product_id: int, customer_id: int, num_threads: int = 20):
    """
    Executes 20 concurrent transactions directly against the database engine
    to verify pessimistic locking (SELECT ... FOR UPDATE).
    """
    print(f"\n--- Running Direct Engine Concurrency Test ({num_threads} simultaneous threads) ---")

    def worker(thread_idx: int):
        db = SessionLocal()
        try:
            order_in = OrderCreate(
                customer_id=customer_id,
                items=[OrderItemCreate(product_id=product_id, quantity=1)],
                simulate_payment_failure=False,
                payment_method="CREDIT_CARD"
            )
            res = place_order(order_in, db)
            return {"status": "SUCCESS", "order_id": res.id, "thread": thread_idx}
        except Exception as exc:
            # 409 Conflict HTTPException or rollback
            err_msg = getattr(exc, "detail", str(exc))
            return {"status": "FAILED", "error": err_msg, "thread": thread_idx}
        finally:
            db.close()

    results = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, i) for i in range(1, num_threads + 1)]
        for f in as_completed(futures):
            results.append(f.result())

    # Verify inventory state
    db = SessionLocal()
    try:
        final_inv = db.query(Inventory).filter(Inventory.product_id == product_id).first()
        final_stock = final_inv.quantity
    finally:
        db.close()

    successes = [r for r in results if r["status"] == "SUCCESS"]
    failures = [r for r in results if r["status"] == "FAILED"]

    print("\n========== CONCURRENCY TEST RESULTS ==========")
    print(f"Total Threads Fired:     {num_threads}")
    print(f"Successful Orders:       {len(successes)} (Expected: 5)")
    print(f"Failed / Blocked Orders: {len(failures)}  (Expected: {num_threads - 5})")
    print(f"Final Inventory Stock:   {final_stock} (Expected: 0)")
    print("==============================================")

    assert len(successes) == 5, f"Expected 5 successes, got {len(successes)}"
    assert len(failures) == (num_threads - 5), f"Expected {num_threads - 5} failures, got {len(failures)}"
    assert final_stock == 0, f"Stock went below 0 or was not exhausted: {final_stock}"
    print(">>> VERIFICATION PASSED: Stock never went below 0 and exactly 5 orders succeeded! <<<\n")


def run_http_concurrency_test(product_id: int, customer_id: int, num_threads: int = 20):
    """Fires 20 simultaneous HTTP POST requests to http://localhost:8000/orders."""
    print(f"\n--- Running HTTP API Concurrency Test against {BASE_URL} ---")
    url = f"{BASE_URL}/orders"
    payload = json.dumps({
        "customer_id": customer_id,
        "items": [{"product_id": product_id, "quantity": 1}],
        "simulate_payment_failure": False,
        "payment_method": "CREDIT_CARD"
    }).encode("utf-8")

    def http_worker(thread_idx: int):
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                body = json.loads(response.read().decode("utf-8"))
                return {"status": 201, "order_id": body.get("id"), "thread": thread_idx}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            return {"status": e.code, "error": err_body, "thread": thread_idx}
        except Exception as e:
            return {"status": 500, "error": str(e), "thread": thread_idx}

    results = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(http_worker, i) for i in range(1, num_threads + 1)]
        for f in as_completed(futures):
            results.append(f.result())

    successes = [r for r in results if r["status"] == 201]
    conflicts = [r for r in results if r["status"] == 409]

    print("\n========== HTTP CONCURRENCY RESULTS ==========")
    print(f"Total Requests:      {num_threads}")
    print(f"HTTP 201 Created:    {len(successes)} (Expected: 5)")
    print(f"HTTP 409 Conflict:   {len(conflicts)} (Expected: {num_threads - 5})")
    print("==============================================")

    assert len(successes) == 5, f"Expected 5 successes, got {len(successes)}"
    assert len(conflicts) == 15, f"Expected 15 conflicts, got {len(conflicts)}"
    print(">>> VERIFICATION PASSED: Exactly 5 HTTP requests succeeded and 15 received 409 Conflict! <<<\n")


if __name__ == "__main__":
    prod_id, cust_id = setup_concurrency_product_in_db()

    # Check if HTTP server is running
    server_online = False
    try:
        urllib.request.urlopen(f"{BASE_URL}/", timeout=1)
        server_online = True
    except Exception:
        server_online = False

    if server_online:
        run_http_concurrency_test(prod_id, cust_id, num_threads=20)
    else:
        print("[Info] HTTP server not detected on localhost:8000; testing via direct SQLAlchemy engine.")
        run_direct_db_concurrency_test(prod_id, cust_id, num_threads=20)
