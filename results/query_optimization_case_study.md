# Query Optimization Case Studies — ecommerce_ops (MySQL 8.0)

Environment: MySQL 8.0 primary–replica (Docker), orders table = 200,000 rows.
Method: EXPLAIN for the plan, EXPLAIN ANALYZE for actual cost. Baseline
measured by dropping the index, re-measuring, then restoring the index.

---

## Case 1: Date-range revenue/order lookup

**Query**
```sql
SELECT * FROM orders
WHERE order_date BETWEEN '2025-09-01' AND '2025-09-30 23:59:59';
```

**Problem**
No index on `order_date` → full table scan. EXPLAIN showed `type: ALL`,
`key: NULL`, rows ≈ 194,686. EXPLAIN ANALYZE confirmed the table scan read
all 200,000 rows (~192 ms) and a filter step discarded 94% of them,
returning 11,028 rows in **251 ms** total.

**Fix**
```sql
CREATE INDEX idx_orders_order_date ON orders(order_date);
```

**Result**
Plan changed to `type: range` using `idx_orders_order_date` with index
condition pushdown (`Using index condition`). Scanned ≈ 19,848 index
entries instead of 200,000 rows. Actual time: **42.8 ms**.

**Impact: 251 ms → 42.8 ms (−83%, ~5.9× faster); rows examined −90%.**

**Why it works**
A B-tree index on `order_date` keeps values sorted, so MySQL seeks directly
to '2025-09-01' and reads forward until '2025-09-30' — no need to visit
rows outside the range. ICP filters inside the storage engine, reducing
row lookups further.


---

## Case 2: Customer order history (filter + sort)

**Query**
```sql
SELECT * FROM orders
WHERE customer_id = 12345
ORDER BY order_date DESC;
```

**Problem**
InnoDB's auto-created FK index on `customer_id` handled the filter
(type: ref, 8 rows), but EXPLAIN showed `Using filesort` — the 8 rows
still required a separate sort step. EXPLAIN ANALYZE showed a two-node
plan: Index lookup → Sort, total **20.4 ms**.

**Fix**
```sql
CREATE INDEX idx_orders_customer_date ON orders(customer_id, order_date);
```

**Result**
Plan collapsed to a single node: Index lookup (reverse) using the
composite index. `Using filesort` replaced by `Backward index scan`.
Actual time: **0.919 ms**.

**Impact: 20.4 ms → 0.92 ms (~22× faster); Sort step eliminated.**

**Why it works**
The composite index orders rows by customer_id, then order_date within
each customer — so the matching rows are already sorted. Reading the
index backward satisfies DESC for free. Key lessons: a single-column
index solves filtering but not ordering; composite column order follows
the leftmost-prefix rule (equality column first, sort column second).

---

## Case 3: Top-selling products JOIN + aggregation

**Query**: JOIN 500K order_items with 5K products, GROUP BY product_name,
ORDER BY SUM(quantity) DESC LIMIT 10.

**Problem**
EXPLAIN ANALYZE showed the join itself was cheap (879 ms) but
`Aggregate using temporary table` dominated: grouping 500K joined rows
by a string column took ~2.3 s. Total: **3164 ms**.

**Fix (two-part)**
1. Covering index: `CREATE INDEX idx_oi_product_qty ON order_items(product_id, quantity);`
2. Query rewrite (aggregation pushdown): aggregate order_items by integer
   product_id in a derived table first (500K → 5K rows), then join to
   products for names.

**Result**
- Covering index alone (original query): 3164 → 2312 ms (join phase
  879 → 158 ms via `Covering index lookup`; temp-table aggregation remained).
- Rewrite + covering index: `Covering index scan` + streaming
  `Group aggregate` (no temporary table); optimizer applied LIMIT before
  the join, doing only 10 primary-key lookups into products. **162 ms**.

**Impact: 3164 ms → 162 ms (~19.5× faster).**

**Why it works**
The covering index makes the scan index-only and pre-sorted by product_id,
enabling streaming aggregation without a temp table. Indexing alone could
not fix the string GROUP BY — query rewriting moved the aggregation to
where the index could serve it. Lesson: locate the real bottleneck in the
plan tree before choosing the fix.

---

## Case 4: Delayed shipments (equality + range filter)

**Query**
```sql
SELECT * FROM shipments
WHERE status = 'delayed' AND shipped_at >= '2026-03-01';
```

**Problem**
Full table scan (type: ALL, 200K rows, 347 ms). `filtered: 3.33` —
the optimizer knew ~97% of scanned rows would be discarded but had
no index to avoid it.

**Fix**
```sql
CREATE INDEX idx_shipments_status_date ON shipments(status, shipped_at);
```
Column order rule: equality column first, range column second — a range
condition "breaks" index usability for any columns after it.

**Result**
type: range, key_len = 88 (82 bytes for status + 6 for shipped_at,
proving both index layers are used), `filtered: 100.00` (zero waste).
**347 ms → 22.9 ms (~15× faster).**

---

## Case 5: Low-stock alert (range filter + sort — the filesort trade-off)

**Query**
```sql
SELECT * FROM inventory
WHERE stock_quantity < 10 ORDER BY updated_at DESC;
```

**Baseline**: full scan, 5000 rows examined, filter to 41, then sort. 18.6 ms.
(Optimizer estimate `filtered: 33.33` vs actual 0.8% — estimates can be
far off; trust EXPLAIN ANALYZE.)

**Fix**: `CREATE INDEX idx_inventory_stock_updated ON inventory(stock_quantity, updated_at);`

**Result**: type: range, 41 rows examined, **0.044 ms (~420×)** — but
`Using filesort` remains. A range on the first column spans multiple
index segments (qty 0–9), each internally ordered by updated_at but not
globally — unlike Case 2 where equality pinned one segment. key_len = 4
confirms only the first column was used for the seek.

**Judgment**: sorting 41 rows is negligible; the index delivered the real
win (rows examined −99%). Not every filesort is worth eliminating.
Bonus: `Using index` — the 3-column table is fully covered because InnoDB
secondary indexes carry the primary key.