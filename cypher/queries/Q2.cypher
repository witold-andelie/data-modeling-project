MATCH (o:Order)-[:PLACED_BY]->(:CustomerRecord)-[:IDENTIFIES]->(c:Customer)
WHERE o.purchased_at >= $start AND o.purchased_at < $end
OPTIONAL MATCH (p:Payment)-[:PAYS]->(o)
WITH c, o, sum(coalesce(p.amount_cents, 0)) AS paid
RETURN c.customer_id AS customer_id, count(o) AS order_count, sum(paid) AS payment_total_cents
ORDER BY customer_id;
