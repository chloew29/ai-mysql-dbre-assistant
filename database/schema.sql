-- 清掉之前的测试表
DROP TABLE IF EXISTS replication_test;

-- 1. customers
CREATE TABLE customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name   VARCHAR(100) NOT NULL,
    email       VARCHAR(150) NOT NULL,
    city        VARCHAR(80),
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. categories
CREATE TABLE categories (
    category_id   INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(80) NOT NULL
);

-- 3. products
CREATE TABLE products (
    product_id   INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    category_id  INT,
    price        DECIMAL(10,2) NOT NULL,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- 4. inventory
CREATE TABLE inventory (
    product_id     INT PRIMARY KEY,
    stock_quantity INT NOT NULL DEFAULT 0,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- 5. orders
CREATE TABLE orders (
    order_id     INT AUTO_INCREMENT PRIMARY KEY,
    customer_id  INT NOT NULL,
    order_date   DATETIME NOT NULL,
    status       VARCHAR(20) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- 6. order_items
CREATE TABLE order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id      INT NOT NULL,
    product_id    INT NOT NULL,
    quantity      INT NOT NULL,
    unit_price    DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id)   REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- 7. payments
CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id   INT NOT NULL,
    amount     DECIMAL(12,2) NOT NULL,
    method     VARCHAR(30) NOT NULL,
    status     VARCHAR(20) NOT NULL,
    paid_at    DATETIME,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- 8. shipments
CREATE TABLE shipments (
    shipment_id  INT AUTO_INCREMENT PRIMARY KEY,
    order_id     INT NOT NULL,
    status       VARCHAR(20) NOT NULL,
    shipped_at   DATETIME,
    delivered_at DATETIME,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- 9. reviews
CREATE TABLE reviews (
    review_id   INT AUTO_INCREMENT PRIMARY KEY,
    product_id  INT NOT NULL,
    customer_id INT NOT NULL,
    rating      TINYINT NOT NULL,
    comment     VARCHAR(500),
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id)  REFERENCES products(product_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- 10. audit_logs
CREATE TABLE audit_logs (
    log_id     BIGINT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    action     VARCHAR(10) NOT NULL,
    record_id  INT,
    changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);