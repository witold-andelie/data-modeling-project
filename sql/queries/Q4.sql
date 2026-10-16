-- Find buyers connected to sellers appearing on low-rated orders.
-- Both the seed orders and buyer orders must lie inside the observation window.
WITH flagged_sellers AS (
 SELECT DISTINCT i.seller_id
 FROM order_items i JOIN orders o ON o.order_id = i.order_id
 JOIN reviews r ON r.order_id = o.order_id
 WHERE r.score <= %(low_score)s AND o.purchased_at >= %(start)s AND o.purchased_at < %(end)s
)
SELECT DISTINCT i.seller_id, cr.customer_id
FROM flagged_sellers f JOIN order_items i ON i.seller_id = f.seller_id
JOIN orders o ON o.order_id = i.order_id
JOIN customer_records cr ON cr.record_id = o.record_id
WHERE o.purchased_at >= %(start)s AND o.purchased_at < %(end)s
ORDER BY i.seller_id, cr.customer_id;
