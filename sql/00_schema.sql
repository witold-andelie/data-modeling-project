-- C1 keys; C2 references; C3 money; C4 scores; C5 sequence numbers.
-- BRL money uses integer cents in both engines. No procedures or triggers.
CREATE TABLE IF NOT EXISTS project_snapshot (
  singleton INT PRIMARY KEY CHECK (singleton = 1),
  dataset_id CHAR(64) NOT NULL,
  status VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
  customer_id CHAR(32) NOT NULL,
  CHECK (customer_id <> ''),
  PRIMARY KEY (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS customer_records (
  record_id CHAR(32) NOT NULL,
  customer_id CHAR(32) NOT NULL,
  zip_prefix VARCHAR(5) NOT NULL,
  city VARCHAR(100) NOT NULL,
  state CHAR(2) NOT NULL,
  CHECK (record_id <> ''),
  PRIMARY KEY (record_id),
  FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS categories (
  category_name VARCHAR(100) NOT NULL,
  CHECK (category_name <> ''),
  PRIMARY KEY (category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS products (
  product_id CHAR(32) NOT NULL,
  category_name VARCHAR(100) NULL,
  weight_g INT NULL,
  CHECK (product_id <> ''),
  PRIMARY KEY (product_id),
  FOREIGN KEY (category_name) REFERENCES categories(category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS sellers (
  seller_id CHAR(32) NOT NULL,
  zip_prefix VARCHAR(5) NOT NULL,
  city VARCHAR(100) NOT NULL,
  state CHAR(2) NOT NULL,
  CHECK (seller_id <> ''),
  PRIMARY KEY (seller_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS orders (
  order_id CHAR(32) NOT NULL,
  record_id CHAR(32) NOT NULL,
  status VARCHAR(30) NOT NULL,
  purchased_at DATETIME NOT NULL,
  approved_at DATETIME NULL,
  delivered_at DATETIME NULL,
  estimated_at DATETIME NULL,
  CHECK (order_id <> ''),
  PRIMARY KEY (order_id),
  FOREIGN KEY (record_id) REFERENCES customer_records(record_id),
  INDEX ix_orders_purchased (purchased_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS order_items (
  order_id CHAR(32) NOT NULL,
  item_number INT NOT NULL,
  product_id CHAR(32) NOT NULL,
  seller_id CHAR(32) NOT NULL,
  price_cents BIGINT NOT NULL,
  freight_cents BIGINT NOT NULL,
  CHECK (order_id <> ''),
  PRIMARY KEY (order_id,item_number),
  FOREIGN KEY (order_id) REFERENCES orders(order_id),
  FOREIGN KEY (product_id) REFERENCES products(product_id),
  FOREIGN KEY (seller_id) REFERENCES sellers(seller_id),
  CHECK (item_number > 0),
  CHECK (price_cents >= 0 AND freight_cents >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS payments (
  order_id CHAR(32) NOT NULL,
  payment_sequence INT NOT NULL,
  payment_type VARCHAR(30) NOT NULL,
  installments INT NOT NULL,
  amount_cents BIGINT NOT NULL,
  CHECK (order_id <> ''),
  PRIMARY KEY (order_id,payment_sequence),
  FOREIGN KEY (order_id) REFERENCES orders(order_id),
  CHECK (payment_sequence > 0),
  CHECK (amount_cents >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS reviews (
  review_record_id VARCHAR(40) NOT NULL,
  source_review_id CHAR(32) NOT NULL,
  order_id CHAR(32) NOT NULL,
  score INT NOT NULL,
  created_at DATETIME NULL,
  CHECK (review_record_id <> ''),
  PRIMARY KEY (review_record_id),
  FOREIGN KEY (order_id) REFERENCES orders(order_id),
  CHECK (score BETWEEN 1 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
