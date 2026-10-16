MATCH (o:Order)-[:PLACED_BY]->(:CustomerRecord)-[:IDENTIFIES]->(c:Customer)
WHERE c.customer_id = $customer_id AND o.purchased_at >= $start AND o.purchased_at < $end
OPTIONAL MATCH (p:Payment)-[:PAYS]->(o)
RETURN o.order_id AS order_id, o.status AS status, o.purchased_at AS purchased_at,
       sum(coalesce(p.amount_cents, 0)) AS payment_total_cents
ORDER BY order_id;
