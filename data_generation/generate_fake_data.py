import pymysql
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
BATCH = 2000  # 每批插 2000 行

# 只连主库(3306)。永远不往从库写!
conn = pymysql.connect(
    host="127.0.0.1", port=3306,
    user="root", password="rootpass",
    database="ecommerce_ops", autocommit=False,
)
cur = conn.cursor()

# 批量加载时临时关掉外键/唯一检查,加快导入(导完再开)
cur.execute("SET FOREIGN_KEY_CHECKS = 0")
cur.execute("SET UNIQUE_CHECKS = 0")

# 各表数据量
N_CATEGORIES = 20
N_CUSTOMERS  = 50_000
N_PRODUCTS   = 5_000
N_ORDERS     = 200_000
N_ORDER_ITEMS= 500_000
N_REVIEWS    = 50_000

ORDER_STATUS    = ['pending', 'paid', 'shipped', 'delivered', 'cancelled']
PAYMENT_METHOD  = ['credit_card', 'paypal', 'apple_pay', 'gift_card']
PAYMENT_STATUS  = ['completed', 'failed', 'refunded']
SHIPMENT_STATUS = ['preparing', 'shipped', 'in_transit', 'delivered', 'delayed']

START = datetime.now() - timedelta(days=540)
def rand_date():
    return START + timedelta(seconds=random.randint(0, 540 * 24 * 3600))

def batched_insert(label, sql, total, row_factory):
    """分批生成并插入,避免一次性占用大量内存。"""
    batch = []
    for n in range(total):
        batch.append(row_factory(n))
        if len(batch) >= BATCH:
            cur.executemany(sql, batch)
            conn.commit()
            batch.clear()
    if batch:
        cur.executemany(sql, batch)
        conn.commit()
    print(f"  {label}: {total} 行完成")

print("开始灌数据...")

# 1. 分类
batched_insert("categories",
    "INSERT INTO categories (category_name) VALUES (%s)",
    N_CATEGORIES, lambda n: (f"Category {n+1}",))

# 2. 客户
batched_insert("customers",
    "INSERT INTO customers (full_name, email, city) VALUES (%s, %s, %s)",
    N_CUSTOMERS, lambda n: (fake.name(), fake.email(), fake.city()))

# 3. 商品
batched_insert("products",
    "INSERT INTO products (product_name, category_id, price) VALUES (%s, %s, %s)",
    N_PRODUCTS, lambda n: (fake.catch_phrase()[:140],
                           random.randint(1, N_CATEGORIES),
                           round(random.uniform(5, 500), 2)))

# 4. 库存(每个商品一行)
batched_insert("inventory",
    "INSERT INTO inventory (product_id, stock_quantity) VALUES (%s, %s)",
    N_PRODUCTS, lambda n: (n + 1, random.randint(0, 1000)))

# 5. 订单
batched_insert("orders",
    "INSERT INTO orders (customer_id, order_date, status, total_amount) VALUES (%s, %s, %s, %s)",
    N_ORDERS, lambda n: (random.randint(1, N_CUSTOMERS), rand_date(),
                         random.choice(ORDER_STATUS), round(random.uniform(10, 2000), 2)))

# 6. 订单明细
batched_insert("order_items",
    "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
    N_ORDER_ITEMS, lambda n: (random.randint(1, N_ORDERS), random.randint(1, N_PRODUCTS),
                              random.randint(1, 5), round(random.uniform(5, 500), 2)))

# 7. 支付(每个订单一笔)
batched_insert("payments",
    "INSERT INTO payments (order_id, amount, method, status, paid_at) VALUES (%s, %s, %s, %s, %s)",
    N_ORDERS, lambda n: (n + 1, round(random.uniform(10, 2000), 2),
                         random.choice(PAYMENT_METHOD), random.choice(PAYMENT_STATUS), rand_date()))

# 8. 物流(每个订单一单)
batched_insert("shipments",
    "INSERT INTO shipments (order_id, status, shipped_at) VALUES (%s, %s, %s)",
    N_ORDERS, lambda n: (n + 1, random.choice(SHIPMENT_STATUS), rand_date()))

# 9. 评价
batched_insert("reviews",
    "INSERT INTO reviews (product_id, customer_id, rating, comment) VALUES (%s, %s, %s, %s)",
    N_REVIEWS, lambda n: (random.randint(1, N_PRODUCTS), random.randint(1, N_CUSTOMERS),
                          random.randint(1, 5), fake.sentence()[:480]))

# 导完恢复检查
cur.execute("SET FOREIGN_KEY_CHECKS = 1")
cur.execute("SET UNIQUE_CHECKS = 1")
conn.commit()
cur.close()
conn.close()
print("全部完成!约 120 万行已写入主库。")