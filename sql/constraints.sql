SELECT 'C1:customers' AS rule, COALESCE(SUM(CASE WHEN customer_id IS NULL OR customer_id = '' THEN n ELSE n-1 END),0) AS violations FROM (SELECT customer_id, COUNT(*) AS n FROM customers GROUP BY customer_id) k
UNION ALL
SELECT 'C1:customer_records' AS rule, COALESCE(SUM(CASE WHEN record_id IS NULL OR record_id = '' THEN n ELSE n-1 END),0) AS violations FROM (SELECT record_id, COUNT(*) AS n FROM customer_records GROUP BY record_id) k
UNION ALL
SELECT 'C1:categories' AS rule, COALESCE(SUM(CASE WHEN category_name IS NULL OR category_name = '' THEN n ELSE n-1 END),0) AS violations FROM (SELECT category_name, COUNT(*) AS n FROM categories GROUP BY category_name) k
UNION ALL
SELECT 'C1:products' AS rule, COALESCE(SUM(CASE WHEN product_id IS NULL OR product_id = '' THEN n ELSE n-1 END),0) AS violations FROM (SELECT product_id, COUNT(*) AS n FROM products GROUP BY product_id) k
UNION ALL
SELECT 'C1:sellers' AS rule, COALESCE(SUM(CASE WHEN seller_id IS NULL OR seller_id = '' THEN n ELSE n-1 END),0) AS violations FROM (SELECT seller_id, COUNT(*) AS n FROM sellers GROUP BY seller_id) k
UNION ALL
SELECT 'C1:orders' AS rule, COALESCE(SUM(CASE WHEN order_id IS NULL OR order_id = '' THEN n ELSE n-1 END),0) AS violations FROM (SELECT order_id, COUNT(*) AS n FROM orders GROUP BY order_id) k
UNION ALL
SELECT 'C1:order_items' AS rule, COALESCE(SUM(CASE WHEN order_id IS NULL OR order_id = '' OR item_number IS NULL THEN n ELSE n-1 END),0) AS violations FROM (SELECT order_id,item_number, COUNT(*) AS n FROM order_items GROUP BY order_id,item_number) k
UNION ALL
SELECT 'C1:payments' AS rule, COALESCE(SUM(CASE WHEN order_id IS NULL OR order_id = '' OR payment_sequence IS NULL THEN n ELSE n-1 END),0) AS violations FROM (SELECT order_id,payment_sequence, COUNT(*) AS n FROM payments GROUP BY order_id,payment_sequence) k
UNION ALL
SELECT 'C1:reviews' AS rule, COALESCE(SUM(CASE WHEN review_record_id IS NULL OR review_record_id = '' THEN n ELSE n-1 END),0) AS violations FROM (SELECT review_record_id, COUNT(*) AS n FROM reviews GROUP BY review_record_id) k
UNION ALL
SELECT 'C2:customer_records.customer_id' AS rule, COUNT(*) AS violations FROM customer_records c LEFT JOIN customers p ON c.customer_id=p.customer_id WHERE c.customer_id IS NOT NULL AND p.customer_id IS NULL
UNION ALL
SELECT 'C2:products.category_name' AS rule, COUNT(*) AS violations FROM products c LEFT JOIN categories p ON c.category_name=p.category_name WHERE c.category_name IS NOT NULL AND p.category_name IS NULL
UNION ALL
SELECT 'C2:orders.record_id' AS rule, COUNT(*) AS violations FROM orders c LEFT JOIN customer_records p ON c.record_id=p.record_id WHERE c.record_id IS NOT NULL AND p.record_id IS NULL
UNION ALL
SELECT 'C2:order_items.order_id' AS rule, COUNT(*) AS violations FROM order_items c LEFT JOIN orders p ON c.order_id=p.order_id WHERE c.order_id IS NOT NULL AND p.order_id IS NULL
UNION ALL
SELECT 'C2:order_items.product_id' AS rule, COUNT(*) AS violations FROM order_items c LEFT JOIN products p ON c.product_id=p.product_id WHERE c.product_id IS NOT NULL AND p.product_id IS NULL
UNION ALL
SELECT 'C2:order_items.seller_id' AS rule, COUNT(*) AS violations FROM order_items c LEFT JOIN sellers p ON c.seller_id=p.seller_id WHERE c.seller_id IS NOT NULL AND p.seller_id IS NULL
UNION ALL
SELECT 'C2:payments.order_id' AS rule, COUNT(*) AS violations FROM payments c LEFT JOIN orders p ON c.order_id=p.order_id WHERE c.order_id IS NOT NULL AND p.order_id IS NULL
UNION ALL
SELECT 'C2:reviews.order_id' AS rule, COUNT(*) AS violations FROM reviews c LEFT JOIN orders p ON c.order_id=p.order_id WHERE c.order_id IS NOT NULL AND p.order_id IS NULL
UNION ALL
SELECT 'C3:order_items' AS rule, COUNT(*) AS violations FROM order_items WHERE price_cents IS NULL OR freight_cents IS NULL OR price_cents < 0 OR freight_cents < 0
UNION ALL
SELECT 'C3:payments' AS rule, COUNT(*) AS violations FROM payments WHERE amount_cents IS NULL OR amount_cents < 0
UNION ALL
SELECT 'C4:reviews' AS rule, COUNT(*) AS violations FROM reviews WHERE score IS NULL OR score < 1 OR score > 5
UNION ALL
SELECT 'C5:order_items' AS rule, COUNT(*) AS violations FROM order_items WHERE item_number IS NULL OR item_number < 1
UNION ALL
SELECT 'C5:payments' AS rule, COUNT(*) AS violations FROM payments WHERE payment_sequence IS NULL OR payment_sequence < 1
ORDER BY rule;
