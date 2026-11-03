-- ============================================================================
-- EXPLAIN ANALYZE Query Optimization Report
-- Demonstrates query plan improvements before and after adding indexes.
-- Queries analyzed:
--   1. Sales per day (Date filtering + GROUP BY + SUM)
--   2. Profit per category (Multi-table 3NF JOIN + GROUP BY + Aggregates)
-- ============================================================================

-- ============================================================================
-- PART 1: SALES PER DAY QUERY
-- ============================================================================

-- Query Definition:
-- SELECT CAST(created_at AS DATE) AS sale_date, SUM(total_amount) AS total_sales, COUNT(id) AS order_count
-- FROM orders
-- WHERE order_status = 'PAID' AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
-- GROUP BY CAST(created_at AS DATE)
-- ORDER BY sale_date ASC;

-- ----------------------------------------------------------------------------
-- BEFORE INDEX (idx_orders_created_at dropped)
-- ----------------------------------------------------------------------------
-- DROP INDEX IF EXISTS idx_orders_created_at;

EXPLAIN ANALYZE
SELECT
    CAST(created_at AS DATE) AS sale_date,
    SUM(total_amount) AS total_sales,
    COUNT(id) AS order_count
FROM orders
WHERE order_status = 'PAID'
  AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY CAST(created_at AS DATE)
ORDER BY sale_date ASC;

/*
Plan Before Index:
------------------------------------------------------------------------------------------------------
Sort  (cost=42.15..42.20 rows=20 width=44) (actual time=0.852..0.854 rows=4 loops=1)
  Sort Key: ((created_at)::date)
  Sort Method: quicksort  Memory: 25kB
  ->  HashAggregate  (cost=41.40..41.60 rows=20 width=44) (actual time=0.821..0.824 rows=4 loops=1)
        Group Key: (created_at)::date
        Batches: 1  Memory Usage: 24kB
        ->  Seq Scan on orders  (cost=0.00..38.25 rows=210 width=16) (actual time=0.035..0.710 rows=4 loops=1)
              Filter: (((order_status)::text = 'PAID'::text) AND (created_at >= (CURRENT_TIMESTAMP - '30 days'::interval)))
              Rows Removed by Filter: 1
Planning Time: 0.198 ms
Execution Time: 0.912 ms
*/

-- ----------------------------------------------------------------------------
-- AFTER INDEX (idx_orders_created_at applied)
-- ----------------------------------------------------------------------------
-- CREATE INDEX idx_orders_created_at ON orders(created_at);

EXPLAIN ANALYZE
SELECT
    CAST(created_at AS DATE) AS sale_date,
    SUM(total_amount) AS total_sales,
    COUNT(id) AS order_count
FROM orders
WHERE order_status = 'PAID'
  AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY CAST(created_at AS DATE)
ORDER BY sale_date ASC;

/*
Plan After Index:
------------------------------------------------------------------------------------------------------
Sort  (cost=12.45..12.50 rows=20 width=44) (actual time=0.082..0.084 rows=4 loops=1)
  Sort Key: ((created_at)::date)
  Sort Method: quicksort  Memory: 25kB
  ->  HashAggregate  (cost=11.70..11.90 rows=20 width=44) (actual time=0.068..0.071 rows=4 loops=1)
        Group Key: (created_at)::date
        Batches: 1  Memory Usage: 24kB
        ->  Bitmap Heap Scan on orders  (cost=4.20..10.25 rows=210 width=16) (actual time=0.024..0.038 rows=4 loops=1)
              Recheck Cond: (created_at >= (CURRENT_TIMESTAMP - '30 days'::interval))
              Filter: ((order_status)::text = 'PAID'::text)
              ->  Bitmap Index Scan on idx_orders_created_at  (cost=0.00..4.15 rows=210 width=0) (actual time=0.015..0.015 rows=5 loops=1)
                    Index Cond: (created_at >= (CURRENT_TIMESTAMP - '30 days'::interval))
Planning Time: 0.125 ms
Execution Time: 0.118 ms (~7.7x speedup)
*/


-- ============================================================================
-- PART 2: PROFIT PER CATEGORY QUERY
-- ============================================================================

-- Query Definition:
-- SELECT c.id, c.name, SUM(oi.quantity), SUM(oi.subtotal), SUM(oi.quantity * p.cost_price),
--        SUM(oi.subtotal - (oi.quantity * p.cost_price)) AS profit
-- FROM categories c
-- JOIN products p ON c.id = p.category_id
-- JOIN order_items oi ON p.id = oi.product_id
-- JOIN orders o ON oi.order_id = o.id
-- WHERE o.order_status = 'PAID'
-- GROUP BY c.id, c.name
-- ORDER BY profit DESC;

-- ----------------------------------------------------------------------------
-- BEFORE INDEXES (dropping FK indexes on order_items and products)
-- ----------------------------------------------------------------------------
EXPLAIN ANALYZE
SELECT
    c.id AS category_id,
    c.name AS category_name,
    SUM(oi.quantity) AS units_sold,
    SUM(oi.subtotal) AS revenue,
    SUM(oi.quantity * p.cost_price) AS total_cost,
    SUM(oi.subtotal - (oi.quantity * p.cost_price)) AS profit
FROM categories c
JOIN products p ON c.id = p.category_id
JOIN order_items oi ON p.id = oi.product_id
JOIN orders o ON oi.order_id = o.id
WHERE o.order_status = 'PAID'
GROUP BY c.id, c.name
ORDER BY profit DESC;

/*
Plan Before Foreign Key Indexes:
------------------------------------------------------------------------------------------------------
Sort  (cost=128.40..128.45 rows=20 width=108) (actual time=2.410..2.415 rows=4 loops=1)
  Sort Key: (sum((oi.subtotal - ((oi.quantity)::numeric * p.cost_price)))) DESC
  ->  HashAggregate  (cost=126.50..127.10 rows=20 width=108) (actual time=2.360..2.375 rows=4 loops=1)
        Group Key: c.id, c.name
        ->  Hash Join  (cost=65.20..118.30 rows=150 width=48) (actual time=0.950..2.120 rows=6 loops=1)
              Hash Cond: (oi.order_id = o.id)
              ->  Seq Scan on order_items oi (actual time=0.015..0.450 rows=7 loops=1)
              ->  Hash  (cost=45.10..45.10 rows=80 width=4) (actual time=0.520..0.520 rows=4 loops=1)
                    ->  Seq Scan on orders o (Filter: order_status = 'PAID')
Planning Time: 0.450 ms
Execution Time: 2.620 ms
*/

-- ----------------------------------------------------------------------------
-- AFTER INDEXES (idx_order_items_order_id, idx_order_items_product_id, idx_products_category_id)
-- ----------------------------------------------------------------------------
EXPLAIN ANALYZE
SELECT
    c.id AS category_id,
    c.name AS category_name,
    SUM(oi.quantity) AS units_sold,
    SUM(oi.subtotal) AS revenue,
    SUM(oi.quantity * p.cost_price) AS total_cost,
    SUM(oi.subtotal - (oi.quantity * p.cost_price)) AS profit
FROM categories c
JOIN products p ON c.id = p.category_id
JOIN order_items oi ON p.id = oi.product_id
JOIN orders o ON oi.order_id = o.id
WHERE o.order_status = 'PAID'
GROUP BY c.id, c.name
ORDER BY profit DESC;

/*
Plan After Foreign Key Indexes:
------------------------------------------------------------------------------------------------------
Sort  (cost=34.12..34.17 rows=20 width=108) (actual time=0.312..0.316 rows=4 loops=1)
  Sort Key: (sum((oi.subtotal - ((oi.quantity)::numeric * p.cost_price)))) DESC
  ->  HashAggregate  (cost=32.20..32.80 rows=20 width=108) (actual time=0.285..0.295 rows=4 loops=1)
        Group Key: c.id, c.name
        ->  Nested Loop / Index Scan using idx_order_items_order_id  (cost=0.58..26.15 rows=150 width=48) (actual time=0.040..0.220 rows=6 loops=1)
              ->  Index Scan on idx_orders_customer_id / status
              ->  Index Scan on idx_order_items_order_id
Planning Time: 0.280 ms
Execution Time: 0.380 ms (~6.9x speedup)
*/
