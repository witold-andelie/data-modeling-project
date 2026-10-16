-- Descriptive co-occurrence counts only; no mining algorithm or recommendation.
WITH order_categories AS (
 SELECT DISTINCT i.order_id, p.category_name
 FROM order_items i JOIN products p ON p.product_id = i.product_id
 JOIN orders o ON o.order_id = i.order_id
 WHERE p.category_name IS NOT NULL AND o.purchased_at >= %(start)s AND o.purchased_at < %(end)s
)
SELECT a.category_name AS category_a, b.category_name AS category_b,
       COUNT(*) AS shared_orders
FROM order_categories a JOIN order_categories b
  ON a.order_id = b.order_id AND a.category_name < b.category_name
GROUP BY a.category_name, b.category_name
ORDER BY category_a, category_b;
