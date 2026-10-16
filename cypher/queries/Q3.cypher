MATCH (r:Review)-[:REVIEWS]->(o:Order)
WHERE o.delivered_at IS NOT NULL AND o.estimated_at IS NOT NULL
  AND o.purchased_at >= $start AND o.purchased_at < $end
WITH o, max(CASE WHEN r.score <= $low_score THEN 1 ELSE 0 END) AS low_rated
WITH CASE WHEN o.delivered_at > o.estimated_at THEN 'late' ELSE 'on_time' END AS delivery_group, low_rated
RETURN delivery_group, count(*) AS reviewed_orders, sum(low_rated) AS low_rated_orders
ORDER BY delivery_group;
