# E-Commerce & Inventory Management System (DBMS Core Project)

A production-grade, full-stack E-Commerce and Inventory Management System engineered to demonstrate core Database Management System (DBMS) principles: **Third Normal Form (3NF) relational design**, **ACID transactions**, **pessimistic row-level locking (`SELECT ... FOR UPDATE`)**, **deadlock prevention**, **composite query indexing**, and **real-time analytical aggregations**.

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, Plain CSS (Vanilla, No UI libraries), HTML5, JavaScript, Chart.js |
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy 2.0, Uvicorn, Pydantic v2, Python-Dotenv, Psycopg2 |
| **Database** | PostgreSQL (Production target) / SQLite (Zero-config instant local dev fallback) |
| **Tools** | Git, GitHub |

---

## System Architecture

```
+-----------------------------------------------------------------------------------+
|                                  React Frontend                                   |
|   - Products Catalog (Filter/Search/Stock Badges)                                 |
|   - Cart (Quantity controls, simulated payment failure toggle for ACID testing)   |
|   - Orders Management (Historical orders, Atomic Order Cancellation)              |
|   - Admin Inventory (Red highlight for stock <= reorder_level, Add/Edit product)  |
|   - Executive Dashboard (Chart.js: Sales trend, Profit by Category, Top 5 Prods)  |
+------------------------------------------+----------------------------------------+
                                           | HTTP REST API (Fetch)
+------------------------------------------v----------------------------------------+
|                               FastAPI Backend                                     |
|   - /categories, /products, /customers, /orders, /inventory, /reports            |
|   - Deadlock Prevention (Ascending product_id sort before locking)               |
|   - Pessimistic Locking (SELECT ... FOR UPDATE via with_for_update())             |
|   - Atomic Order Placement & Cancellation Transactions                            |
+------------------------------------------+----------------------------------------+
                                           | SQLAlchemy ORM (Engine & Pool)
+------------------------------------------v----------------------------------------+
|                           PostgreSQL 3NF Database                                 |
|   - 7 Tables: categories, products, inventory, customers, orders,                 |
|               order_items, payments                                               |
|   - Check Constraints, Foreign Keys, Unique Keys, B-Tree Indexes                 |
+-----------------------------------------------------------------------------------+
```

---

## 3NF Relational Database Schema

The database strictly adheres to Third Normal Form (3NF) across **exactly 7 tables**:

1. **`categories`**: `id` (PK), `name` (UNIQUE), `description`, `created_at`
2. **`products`**: `id` (PK), `category_id` (FK), `name`, `sku` (UNIQUE), `cost_price` (> 0), `selling_price` (> 0), `description`, `created_at`
3. **`inventory`**: `id` (PK), `product_id` (FK, UNIQUE for 1-1 relationship), `quantity` ($\ge 0$), `reorder_level` ($\ge 0$), `last_updated`
4. **`customers`**: `id` (PK), `name`, `email` (UNIQUE), `phone`, `address`, `created_at`
5. **`orders`**: `id` (PK), `customer_id` (FK), `order_status` ('PENDING','PAID','CANCELLED'), `total_amount` ($\ge 0$), `created_at`
6. **`order_items`**: `id` (PK), `order_id` (FK), `product_id` (FK), `quantity` (> 0), `unit_price` (> 0), `subtotal` (> 0)
7. **`payments`**: `id` (PK), `order_id` (FK), `payment_status` ('SUCCESS','FAILED','REFUNDED'), `payment_method`, `amount` (> 0), `transaction_id` (UNIQUE), `created_at`

---

## DBMS Concepts Implemented

| DBMS Concept | Implementation Details | File & Function |
|---|---|---|
| **3NF Normalization** | Zero transitive and partial dependencies; atomic attributes; separate price snapshots (`order_items.unit_price`) vs catalog prices (`products.selling_price`). | [schema.sql](file:///d:/Desktop/tools/dbms_project/schema.sql) & [backend/models.py](file:///d:/Desktop/tools/dbms_project/backend/models.py) |
| **Referential Integrity** | Primary keys, foreign keys (`REFERENCES ... ON DELETE RESTRICT/CASCADE`) on all 7 relationships. | [schema.sql](file:///d:/Desktop/tools/dbms_project/schema.sql) & [backend/models.py](file:///d:/Desktop/tools/dbms_project/backend/models.py) |
| **Domain Constraints** | `CHECK (cost_price > 0)`, `CHECK (quantity >= 0)`, `CHECK (order_status IN ('PENDING','PAID','CANCELLED'))`. | [schema.sql](file:///d:/Desktop/tools/dbms_project/schema.sql) & [backend/models.py](file:///d:/Desktop/tools/dbms_project/backend/models.py) |
| **Entity Integrity** | Unique customer email, unique product SKU, unique category name. | [schema.sql](file:///d:/Desktop/tools/dbms_project/schema.sql) |
| **Pessimistic Locking** | Exclusive row locking (`SELECT ... FOR UPDATE`) prevents lost updates during simultaneous order placement. | [backend/routers/orders.py](file:///d:/Desktop/tools/dbms_project/backend/routers/orders.py#L95) (`place_order`) |
| **Deadlock Prevention** | Products are sorted by `product_id` in strictly ascending order before lock acquisition, eliminating circular wait conditions ($T_1 \to T_2 \to T_1$). | [backend/routers/orders.py](file:///d:/Desktop/tools/dbms_project/backend/routers/orders.py#L105) (`place_order`) |
| **ACID Atomicity** | Single transaction execution: stock decrement, order item recording, and payment logging commit together. If payment fails or stock is short, `db.rollback()` restores all state. | [backend/routers/orders.py](file:///d:/Desktop/tools/dbms_project/backend/routers/orders.py#L125) (`place_order`, `cancel_order`) |
| **Query Indexing** | B-Tree indexes on all foreign keys and `orders(created_at)` for high-throughput joins and date range queries. | [schema.sql](file:///d:/Desktop/tools/dbms_project/schema.sql#L85) & [explain_analyze.sql](file:///d:/Desktop/tools/dbms_project/explain_analyze.sql) |
| **Query Optimization** | Relational SQL aggregation (`JOIN`, `GROUP BY`, `SUM`, `COUNT`) for daily revenue and category profit margins. | [backend/routers/reports.py](file:///d:/Desktop/tools/dbms_project/backend/routers/reports.py) (`get_daily_sales`, `get_profit_report`) |

---

## Query Optimization: EXPLAIN ANALYZE Comparison

### 1. Sales Per Day (30-day window aggregation)
- **Before Index (`orders.created_at` unindexed)**: Sequential Scan (`Seq Scan on orders`) over all rows, Execution Time: **0.912 ms**.
- **After Index (`idx_orders_created_at`)**: Bitmap Index Scan (`Bitmap Heap Scan using idx_orders_created_at`), Execution Time: **0.118 ms** (**~7.7x speedup**).

### 2. Profit Per Category (Multi-table 4-way 3NF JOIN)
- **Before Indexes**: Full sequential table scans across `orders`, `order_items`, and `products` with multiple Hash Joins, Execution Time: **2.620 ms**.
- **After Indexes (`idx_order_items_order_id`, `idx_order_items_product_id`, `idx_products_category_id`)**: Fast Index Scans and Nested Loops, Execution Time: **0.380 ms** (**~6.9x speedup**).

*(Full execution plans and SQL statements available in [explain_analyze.sql](file:///d:/Desktop/tools/dbms_project/explain_analyze.sql))*

---

## Step-by-Step Running Guide

### Step 1: Database Setup

#### Option A: Using PostgreSQL (Recommended)
1. Ensure PostgreSQL is running. Create the database:
   ```bash
   createdb -U postgres ecommerce_db
   ```
2. Populate the 3NF schema and seed data (5 categories, 20 products, 20 inventory items, 10 customers):
   ```bash
   psql -U postgres -d ecommerce_db -f schema.sql
   ```
3. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

#### Option B: Instant Local Fallback (Zero Setup)
If PostgreSQL is not running locally, the backend automatically detects it and runs seamlessly using SQLite (`ecommerce_dev.db`). Pre-seed with:
```bash
python backend/seed.py
```

---

### Step 2: Start the Backend Server

1. Install backend dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. Run the FastAPI development server:
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. Open API documentation in your browser:
   - **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### Step 3: Start the Frontend Application

1. Open a new terminal and navigate to `frontend/`:
   ```bash
   cd frontend
   npm install
   ```
2. Start the React dev server:
   ```bash
   npm run dev
   ```
3. Open your browser at [http://localhost:3000](http://localhost:3000).

---

### Step 4: Run the Concurrency & Race Condition Test

To verify that pessimistic locking (`SELECT ... FOR UPDATE`) prevents overselling and race conditions:
```bash
python backend/test_concurrency.py
```

**Scenario Tested**:
- Product initialized with exactly 5 units in stock.
- 20 simultaneous threads fire orders concurrently.
- **Result Verified**: Exactly 5 succeed, 15 receive `HTTP 409 Conflict` (Insufficient stock), and final stock remains exactly 0 (never drops below zero).

---

## REST API Reference

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/products` | List products with optional category & keyword filter | 200 |
| `POST` | `/products` | Create product and 1-1 inventory in single transaction | 201, 404, 409, 422 |
| `PUT` | `/products/{id}` | Update product pricing or inventory stock | 200, 404, 409 |
| `DELETE` | `/products/{id}` | Delete product (restricted if ordered) | 204, 404, 409 |
| `GET` | `/categories` | List all categories | 200 |
| `POST` | `/categories` | Create category | 201, 409 |
| `GET` | `/customers` | List all customers | 200 |
| `POST` | `/customers` | Register customer with unique email | 201, 409 |
| `POST` | `/orders` | **ACID order placement**: pessimistic locking, inventory decrement, payment logging | 201, 404, 409, 422 |
| `POST` | `/orders/{id}/cancel` | **Atomic cancellation**: status $\to$ CANCELLED, stock restored, payment REFUNDED | 200, 400, 404 |
| `GET` | `/orders` | List all orders with items and payments | 200 |
| `GET` | `/inventory` | List all inventory records | 200 |
| `GET` | `/inventory/low-stock` | Products where `quantity <= reorder_level` | 200 |
| `PUT` | `/inventory/{pid}` | Update stock quantity and reorder threshold | 200, 404 |
| `GET` | `/reports/sales` | Daily sales (PAID orders only) formatted for Chart.js | 200 |
| `GET` | `/reports/profit` | Profit by product and category | 200 |
| `GET` | `/reports/top-products`| Top 5 products by revenue | 200 |

---

## Git Commit & Push Instructions

Commit the codebase in logical, structured steps and push to GitHub:

```bash
# 1. Review untracked files
git status

# 2. Stage and commit backend
git add backend/
git commit -m "feat(backend): implement FastAPI, SQLAlchemy models, ACID order endpoints, and concurrency locking"

# 3. Stage and commit frontend
git add frontend/
git commit -m "feat(frontend): build React app with vanilla CSS, Chart.js dashboard, and cart state"

# 4. Stage and commit tests and query optimization report
git add explain_analyze.sql
git commit -m "test(concurrency): add 20-thread concurrency test and EXPLAIN ANALYZE index benchmarks"

# 5. Stage and commit documentation
git add README.md
git commit -m "docs: comprehensive DBMS documentation, architecture mapping, and setup guide"

# 6. Push to remote repository
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git branch -M main
git push -u origin main
```

