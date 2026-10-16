-- An order is low-rated if ANY retained source review meets the threshold.
-- Count only orders with known delivery/estimate and at least one review.
SELECT CASE WHEN o.delivered_at > o.estimated_at THEN 'late' ELSE 'on_time' END AS delivery_group,
       COUNT(*) AS reviewed_orders,
       SUM(r.low_rated) AS low_rated_orders
FROM orders o
JOIN (SELECT order_id, MAX(CASE WHEN score <= %(low_score)s THEN 1 ELSE 0 END) AS low_rated
      FROM reviews GROUP BY order_id) r ON r.order_id = o.order_id
WHERE o.delivered_at IS NOT NULL AND o.estimated_at IS NOT NULL
  AND o.purchased_at >= %(start)s AND o.purchased_at < %(end)s
GROUP BY delivery_group ORDER BY delivery_group;
