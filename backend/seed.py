import os
import sys
from decimal import Decimal
from datetime import datetime, timezone, timedelta

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, SessionLocal, Base
from backend.models import Category, Product, Inventory, Customer, Order, OrderItem, Payment

def seed_database():
    """
    Seeds the database with:
    - 5 Categories
    - 20 Products (4 per category)
    - 20 Inventory records (Products 1-1 Inventory, some low-stock <= 5)
    - 10 Customers
    - Sample completed (PAID) and cancelled orders for reports
    """
    print("Creating tables if not present...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(Category).first():
            print("Database already contains records. Skipping seed.")
            return

        print("Seeding 5 Categories...")
        categories_data = [
            ("Electronics", "Gadgets, computing hardware, and smart electronic accessories"),
            ("Apparel & Fashion", "Men and women clothing, everyday wear, and apparel accessories"),
            ("Home & Kitchen", "Home appliances, kitchenware, and living space organizers"),
            ("Books & Stationery", "Technical textbooks, stationery, and notebooks"),
            ("Fitness & Outdoors", "Sports equipment, workout gear, and outdoor activity essentials")
        ]
        cat_objs = []
        for name, desc in categories_data:
            c = Category(name=name, description=desc)
            db.add(c)
            cat_objs.append(c)
        db.flush()

        print("Seeding 20 Products & Inventory...")
        products_data = [
            # Cat 1: Electronics
            (cat_objs[0].id, "ProBook 15 Gen 2 Laptop", "ELEC-LAP-001", Decimal("750.00"), Decimal("999.99"), "High-performance laptop with 16GB RAM and 512GB SSD", 15, 5),
            (cat_objs[0].id, "Wireless Noise-Cancelling Headphones", "ELEC-AUD-002", Decimal("80.00"), Decimal("149.99"), "Over-ear Bluetooth headphones with active noise cancellation", 4, 5), # Low stock
            (cat_objs[0].id, "Ergonomic Optical Mouse", "ELEC-ACC-003", Decimal("18.00"), Decimal("39.99"), "Rechargeable wireless ergonomic mouse with adjustable DPI", 2, 5), # Low stock
            (cat_objs[0].id, "Mechanical RGB Keyboard", "ELEC-ACC-004", Decimal("45.00"), Decimal("89.99"), "Compact mechanical keyboard with blue switches and RGB backlight", 25, 5),

            # Cat 2: Apparel
            (cat_objs[1].id, "Classic Cotton Crewneck T-Shirt", "CLOTH-TSH-001", Decimal("8.00"), Decimal("24.99"), "100% breathable organic combed cotton t-shirt in Navy Blue", 50, 10),
            (cat_objs[1].id, "Slim Fit Stretch Denim Jeans", "CLOTH-JEA-002", Decimal("22.00"), Decimal("59.99"), "Comfortable mid-rise denim jeans with flexible stretch fabric", 18, 8),
            (cat_objs[1].id, "Water-Resistant Windbreaker Jacket", "CLOTH-JAC-003", Decimal("35.00"), Decimal("79.99"), "Lightweight packable hooded jacket for rainy and windy weather", 3, 5), # Low stock
            (cat_objs[1].id, "Athletic Cushion Running Socks (3-Pack)", "CLOTH-SCK-004", Decimal("4.50"), Decimal("14.99"), "Moisture-wicking athletic crew socks with arch support", 60, 15),

            # Cat 3: Home & Kitchen
            (cat_objs[2].id, "Stainless Steel Chef Knife 8-Inch", "HOME-KNF-001", Decimal("19.00"), Decimal("44.99"), "High-carbon Japanese stainless steel precision chef knife", 12, 5),
            (cat_objs[2].id, "Electric Drip Coffee Maker 12-Cup", "HOME-COF-002", Decimal("32.00"), Decimal("69.99"), "Programmable coffee maker with glass carafe and warming plate", 5, 5), # Low stock
            (cat_objs[2].id, "Double-Wall Insulated Steel Tumbler", "HOME-TMB-003", Decimal("7.50"), Decimal("22.99"), "20oz vacuum-insulated stainless steel tumbler with spill-proof lid", 40, 10),
            (cat_objs[2].id, "HEPA Air Purifier for Home", "HOME-AIR-004", Decimal("55.00"), Decimal("119.99"), "3-stage filtration quiet air purifier for bedroom and living room", 1, 4), # Low stock

            # Cat 4: Books
            (cat_objs[3].id, "Database System Concepts (8th Ed)", "BOOK-DBS-001", Decimal("48.00"), Decimal("89.99"), "Definitive reference guide on relational theory, SQL, and ACID transactions", 14, 5),
            (cat_objs[3].id, "Designing Data-Intensive Applications", "BOOK-SYS-002", Decimal("28.00"), Decimal("52.99"), "Reliable, scalable, and maintainable distributed data systems", 22, 5),
            (cat_objs[3].id, "Dot Grid Hardcover Journal (A5)", "BOOK-JRN-003", Decimal("6.00"), Decimal("16.99"), "160-page premium 120gsm bamboo paper hardcover notebook", 35, 10),
            (cat_objs[3].id, "Fineliner Precision Gel Pens (Set of 10)", "BOOK-PEN-004", Decimal("5.00"), Decimal("13.99"), "0.5mm archival non-bleeding ink pens for drafting and notes", 45, 10),

            # Cat 5: Fitness
            (cat_objs[4].id, "Adjustable Cast Iron Dumbbells 50lb Set", "FITN-DMB-001", Decimal("70.00"), Decimal("139.99"), "Pair of adjustable dumbbell handles with weight plates and collars", 8, 4),
            (cat_objs[4].id, "High-Density Non-Slip Yoga Mat", "FITN-MAT-002", Decimal("12.00"), Decimal("29.99"), "6mm eco-friendly cushioned workout mat with carrying strap", 20, 5),
            (cat_objs[4].id, "Speed Cable Skipping Rope", "FITN-ROP-003", Decimal("3.50"), Decimal("11.99"), "Ball-bearing adjustable tangle-free jump rope for cardio", 30, 8),
            (cat_objs[4].id, "Deep Muscle Massage Gun", "FITN-MSG-004", Decimal("38.00"), Decimal("84.99"), "Percussive therapy handheld muscle massager with 6 speed heads", 3, 5), # Low stock
        ]

        prod_objs = []
        for cat_id, name, sku, cost, sell, desc, qty, reorder in products_data:
            p = Product(
                category_id=cat_id,
                name=name,
                sku=sku,
                cost_price=cost,
                selling_price=sell,
                description=desc
            )
            db.add(p)
            db.flush()
            inv = Inventory(
                product_id=p.id,
                quantity=qty,
                reorder_level=reorder
            )
            db.add(inv)
            prod_objs.append(p)
        db.flush()

        print("Seeding 10 Customers...")
        customers_data = [
            ("Alice Johnson", "alice.johnson@example.com", "+1-555-0101", "742 Evergreen Terrace, Springfield, OR"),
            ("Bob Smith", "bob.smith@example.com", "+1-555-0102", "123 Elm Street, Austin, TX"),
            ("Charlie Brown", "charlie.brown@example.com", "+1-555-0103", "456 Maple Avenue, Seattle, WA"),
            ("Diana Prince", "diana.prince@example.com", "+1-555-0104", "789 Gateway Blvd, San Francisco, CA"),
            ("Ethan Hunt", "ethan.hunt@example.com", "+1-555-0105", "100 Mission Street, New York, NY"),
            ("Fiona Gallagher", "fiona.gallagher@example.com", "+1-555-0106", "211 South Michigan Ave, Chicago, IL"),
            ("George Clark", "george.clark@example.com", "+1-555-0107", "340 Pine Road, Denver, CO"),
            ("Hannah Abbott", "hannah.abbott@example.com", "+1-555-0108", "890 Ocean Drive, Miami, FL"),
            ("Ian Wright", "ian.wright@example.com", "+1-555-0109", "512 Oak Lane, Boston, MA"),
            ("Julia Roberts", "julia.roberts@example.com", "+1-555-0110", "654 Sunset Blvd, Los Angeles, CA"),
        ]
        cust_objs = []
        for name, email, phone, addr in customers_data:
            c = Customer(name=name, email=email, phone=phone, address=addr)
            db.add(c)
            cust_objs.append(c)
        db.flush()

        print("Seeding Sample Orders, OrderItems, and Payments for Charts...")
        now = datetime.now(timezone.utc)
        orders_data = [
            (cust_objs[0].id, "PAID", Decimal("1039.98"), now - timedelta(days=3), [(prod_objs[0], 1), (prod_objs[2], 1)]),
            (cust_objs[1].id, "PAID", Decimal("149.99"),  now - timedelta(days=2), [(prod_objs[1], 1)]),
            (cust_objs[2].id, "PAID", Decimal("219.98"),  now - timedelta(days=1), [(prod_objs[16], 1), (prod_objs[6], 1)]),
            (cust_objs[3].id, "PAID", Decimal("89.99"),   now - timedelta(hours=12), [(prod_objs[12], 1)]),
            (cust_objs[4].id, "CANCELLED", Decimal("119.99"), now - timedelta(hours=6), [(prod_objs[11], 1)]),
        ]

        for i, (cid, st, tot, dt, items_list) in enumerate(orders_data, start=1):
            ord_obj = Order(
                customer_id=cid,
                order_status=st,
                total_amount=tot,
                created_at=dt
            )
            db.add(ord_obj)
            db.flush()

            for prod, q in items_list:
                item = OrderItem(
                    order_id=ord_obj.id,
                    product_id=prod.id,
                    quantity=q,
                    unit_price=prod.selling_price,
                    subtotal=prod.selling_price * q
                )
                db.add(item)

            pay_st = "SUCCESS" if st == "PAID" else "REFUNDED"
            payment = Payment(
                order_id=ord_obj.id,
                payment_status=pay_st,
                payment_method="CREDIT_CARD",
                amount=tot,
                transaction_id=f"TXN-SEED-00{i}",
                created_at=dt
            )
            db.add(payment)

        db.commit()
        print("Database seeded successfully with 5 categories, 20 products, 20 inventory items, 10 customers, and sample orders!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
