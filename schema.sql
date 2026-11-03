-- ============================================================================
-- E-Commerce & Inventory Management System Database Schema (PostgreSQL)
-- Schema Definition & Seed Data (Normalized to 3NF)
-- Exactly 7 Tables: Categories, Products, Customers, Orders, Order_Items,
--                   Payments, Inventory
-- ============================================================================

-- Drop tables if they already exist (in reverse dependency order)
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS inventory CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

-- ----------------------------------------------------------------------------
-- 1. Categories Table (1-N with Products)
-- ----------------------------------------------------------------------------
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 2. Products Table (Belongs to Category, 1-1 with Inventory, 1-N with Order_Items)
-- Contains cost_price and selling_price for profit margin calculations.
-- ----------------------------------------------------------------------------
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(50) NOT NULL UNIQUE,
    cost_price NUMERIC(10, 2) NOT NULL CHECK (cost_price > 0),
    selling_price NUMERIC(10, 2) NOT NULL CHECK (selling_price > 0),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 3. Inventory Table (1-1 relationship with Products)
-- Tracks quantity in stock and reorder threshold for low-stock alerts.
-- ----------------------------------------------------------------------------
CREATE TABLE inventory (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL UNIQUE REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    reorder_level INTEGER NOT NULL DEFAULT 5 CHECK (reorder_level >= 0),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 4. Customers Table (1-N with Orders)
-- ----------------------------------------------------------------------------
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50),
    address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 5. Orders Table (Belongs to Customer, 1-N with Order_Items and Payments)
-- ----------------------------------------------------------------------------
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    order_status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (order_status IN ('PENDING', 'PAID', 'CANCELLED')),
    total_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (total_amount >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 6. Order_Items Table (Weak entity / bridge between Orders and Products)
-- ----------------------------------------------------------------------------
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price > 0),
    subtotal NUMERIC(12, 2) NOT NULL CHECK (subtotal > 0)
);

-- ----------------------------------------------------------------------------
-- 7. Payments Table (1-N with Orders to support payment attempts/refunds)
-- ----------------------------------------------------------------------------
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    payment_status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS' CHECK (payment_status IN ('SUCCESS', 'FAILED', 'REFUNDED')),
    payment_method VARCHAR(50) NOT NULL DEFAULT 'CREDIT_CARD',
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    transaction_id VARCHAR(100) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES
-- Indexes on all foreign keys and Orders.created_at for performance & fast joins
-- ============================================================================
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_inventory_product_id ON inventory(product_id);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_payments_order_id ON payments(order_id);

-- ============================================================================
-- SEED DATA
-- 5 Categories, 20 Products (with matching Inventory), 10 Customers
-- ============================================================================

-- Seed 5 Categories
INSERT INTO categories (id, name, description) VALUES
(1, 'Electronics', 'Gadgets, computing hardware, and smart electronic accessories'),
(2, 'Apparel & Fashion', 'Men and women clothing, everyday wear, and apparel accessories'),
(3, 'Home & Kitchen', 'Home appliances, kitchenware, and living space organizers'),
(4, 'Books & Stationery', 'Technical textbooks, stationery, and notebooks'),
(5, 'Fitness & Outdoors', 'Sports equipment, workout gear, and outdoor activity essentials');

ALTER SEQUENCE categories_id_seq RESTART WITH 6;

-- Seed 20 Products
INSERT INTO products (id, category_id, name, sku, cost_price, selling_price, description) VALUES
-- Category 1: Electronics
(1, 1, 'ProBook 15 Gen 2 Laptop', 'ELEC-LAP-001', 750.00, 999.99, 'High-performance laptop with 16GB RAM and 512GB SSD'),
(2, 1, 'Wireless Noise-Cancelling Headphones', 'ELEC-AUD-002', 80.00, 149.99, 'Over-ear Bluetooth headphones with active noise cancellation'),
(3, 1, 'Ergonomic Optical Mouse', 'ELEC-ACC-003', 18.00, 39.99, 'Rechargeable wireless ergonomic mouse with adjustable DPI'),
(4, 1, 'Mechanical RGB Keyboard', 'ELEC-ACC-004', 45.00, 89.99, 'Compact mechanical keyboard with blue switches and RGB backlight'),

-- Category 2: Apparel & Fashion
(5, 2, 'Classic Cotton Crewneck T-Shirt', 'CLOTH-TSH-001', 8.00, 24.99, '100% breathable organic combed cotton t-shirt in Navy Blue'),
(6, 2, 'Slim Fit Stretch Denim Jeans', 'CLOTH-JEA-002', 22.00, 59.99, 'Comfortable mid-rise denim jeans with flexible stretch fabric'),
(7, 2, 'Water-Resistant Windbreaker Jacket', 'CLOTH-JAC-003', 35.00, 79.99, 'Lightweight packable hooded jacket for rainy and windy weather'),
(8, 2, 'Athletic Cushion Running Socks (3-Pack)', 'CLOTH-SCK-004', 4.50, 14.99, 'Moisture-wicking athletic crew socks with arch support'),

-- Category 3: Home & Kitchen
(9, 3, 'Stainless Steel Chef Knife 8-Inch', 'HOME-KNF-001', 19.00, 44.99, 'High-carbon Japanese stainless steel precision chef knife'),
(10, 3, 'Electric Drip Coffee Maker 12-Cup', 'HOME-COF-002', 32.00, 69.99, 'Programmable coffee maker with glass carafe and warming plate'),
(11, 3, 'Double-Wall Insulated Steel Tumbler', 'HOME-TMB-003', 7.50, 22.99, '20oz vacuum-insulated stainless steel tumbler with spill-proof lid'),
(12, 3, 'HEPA Air Purifier for Home', 'HOME-AIR-004', 55.00, 119.99, '3-stage filtration quiet air purifier for bedroom and living room'),

-- Category 4: Books & Stationery
(13, 4, 'Database System Concepts (8th Ed)', 'BOOK-DBS-001', 48.00, 89.99, 'Definitive reference guide on relational theory, SQL, and ACID transactions'),
(14, 4, 'Designing Data-Intensive Applications', 'BOOK-SYS-002', 28.00, 52.99, 'Reliable, scalable, and maintainable distributed data systems'),
(15, 4, 'Dot Grid Hardcover Journal (A5)', 'BOOK-JRN-003', 6.00, 16.99, '160-page premium 120gsm bamboo paper hardcover notebook'),
(16, 4, 'Fineliner Precision Gel Pens (Set of 10)', 'BOOK-PEN-004', 5.00, 13.99, '0.5mm archival non-bleeding ink pens for drafting and notes'),

-- Category 5: Fitness & Outdoors
(17, 5, 'Adjustable Cast Iron Dumbbells 50lb Set', 'FITN-DMB-001', 70.00, 139.99, 'Pair of adjustable dumbbell handles with weight plates and collars'),
(18, 5, 'High-Density Non-Slip Yoga Mat', 'FITN-MAT-002', 12.00, 29.99, '6mm eco-friendly cushioned workout mat with carrying strap'),
(19, 5, 'Speed Cable Skipping Rope', 'FITN-ROP-003', 3.50, 11.99, 'Ball-bearing adjustable tangle-free jump rope for cardio'),
(20, 5, 'Deep Muscle Massage Gun', 'FITN-MSG-004', 38.00, 84.99, 'Percussive therapy handheld muscle massager with 6 speed heads');

ALTER SEQUENCE products_id_seq RESTART WITH 21;

-- Seed 20 Inventory Records (Products 1-1 Inventory)
-- Notice some items have low stock (<= reorder_level 5) to demonstrate low-stock alert
INSERT INTO inventory (product_id, quantity, reorder_level) VALUES
(1, 15, 5),   -- Laptop: Healthy
(2, 4, 5),    -- Headphones: LOW STOCK (4 <= 5)
(3, 2, 5),    -- Mouse: LOW STOCK (2 <= 5)
(4, 25, 5),   -- Keyboard: Healthy
(5, 50, 10),  -- T-Shirt: Healthy
(6, 18, 8),   -- Jeans: Healthy
(7, 3, 5),    -- Jacket: LOW STOCK (3 <= 5)
(8, 60, 15),  -- Socks: Healthy
(9, 12, 5),   -- Knife: Healthy
(10, 5, 5),   -- Coffee Maker: LOW STOCK (5 <= 5)
(11, 40, 10), -- Tumbler: Healthy
(12, 1, 4),   -- Air Purifier: LOW STOCK (1 <= 4)
(13, 14, 5),  -- Database Book: Healthy
(14, 22, 5),  -- System Design Book: Healthy
(15, 35, 10), -- Journal: Healthy
(16, 45, 10), -- Gel Pens: Healthy
(17, 8, 4),   -- Dumbbells: Healthy
(18, 20, 5),  -- Yoga Mat: Healthy
(19, 30, 8),  -- Jump Rope: Healthy
(20, 3, 5);   -- Massage Gun: LOW STOCK (3 <= 5)

ALTER SEQUENCE inventory_id_seq RESTART WITH 21;

-- Seed 10 Customers
INSERT INTO customers (id, name, email, phone, address) VALUES
(1, 'Alice Johnson', 'alice.johnson@example.com', '+1-555-0101', '742 Evergreen Terrace, Springfield, OR'),
(2, 'Bob Smith', 'bob.smith@example.com', '+1-555-0102', '123 Elm Street, Austin, TX'),
(3, 'Charlie Brown', 'charlie.brown@example.com', '+1-555-0103', '456 Maple Avenue, Seattle, WA'),
(4, 'Diana Prince', 'diana.prince@example.com', '+1-555-0104', '789 Gateway Blvd, San Francisco, CA'),
(5, 'Ethan Hunt', 'ethan.hunt@example.com', '+1-555-0105', '100 Mission Street, New York, NY'),
(6, 'Fiona Gallagher', 'fiona.gallagher@example.com', '+1-555-0106', '211 South Michigan Ave, Chicago, IL'),
(7, 'George Clark', 'george.clark@example.com', '+1-555-0107', '340 Pine Road, Denver, CO'),
(8, 'Hannah Abbott', 'hannah.abbott@example.com', '+1-555-0108', '890 Ocean Drive, Miami, FL'),
(9, 'Ian Wright', 'ian.wright@example.com', '+1-555-0109', '512 Oak Lane, Boston, MA'),
(10, 'Julia Roberts', 'julia.roberts@example.com', '+1-555-0110', '654 Sunset Blvd, Los Angeles, CA');

ALTER SEQUENCE customers_id_seq RESTART WITH 11;

-- Seed a few historical orders and payments so initial reports / charts show data immediately
INSERT INTO orders (id, customer_id, order_status, total_amount, created_at) VALUES
(1, 1, 'PAID', 1039.98, CURRENT_TIMESTAMP - INTERVAL '3 days'),
(2, 2, 'PAID', 149.99,  CURRENT_TIMESTAMP - INTERVAL '2 days'),
(3, 3, 'PAID', 219.98,  CURRENT_TIMESTAMP - INTERVAL '1 days'),
(4, 4, 'PAID', 89.99,   CURRENT_TIMESTAMP - INTERVAL '12 hours'),
(5, 5, 'CANCELLED', 119.99, CURRENT_TIMESTAMP - INTERVAL '6 hours');

ALTER SEQUENCE orders_id_seq RESTART WITH 6;

INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, subtotal) VALUES
(1, 1, 1, 1, 999.99, 999.99),
(2, 1, 3, 1, 39.99, 39.99),
(3, 2, 2, 1, 149.99, 149.99),
(4, 3, 17, 1, 139.99, 139.99),
(5, 3, 7, 1, 79.99, 79.99),
(6, 4, 13, 1, 89.99, 89.99),
(7, 5, 12, 1, 119.99, 119.99);

ALTER SEQUENCE order_items_id_seq RESTART WITH 8;

INSERT INTO payments (id, order_id, payment_status, payment_method, amount, transaction_id, created_at) VALUES
(1, 1, 'SUCCESS', 'CREDIT_CARD', 1039.98, 'TXN-INIT-001', CURRENT_TIMESTAMP - INTERVAL '3 days'),
(2, 2, 'SUCCESS', 'DEBIT_CARD', 149.99, 'TXN-INIT-002', CURRENT_TIMESTAMP - INTERVAL '2 days'),
(3, 3, 'SUCCESS', 'PAYPAL', 219.98, 'TXN-INIT-003', CURRENT_TIMESTAMP - INTERVAL '1 days'),
(4, 4, 'SUCCESS', 'CREDIT_CARD', 89.99, 'TXN-INIT-004', CURRENT_TIMESTAMP - INTERVAL '12 hours'),
(5, 5, 'REFUNDED', 'CREDIT_CARD', 119.99, 'TXN-INIT-005', CURRENT_TIMESTAMP - INTERVAL '6 hours');

ALTER SEQUENCE payments_id_seq RESTART WITH 6;
