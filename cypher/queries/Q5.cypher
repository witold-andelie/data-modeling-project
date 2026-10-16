MATCH (a:Category)<-[:IN_CATEGORY]-(:Product)<-[:FOR_PRODUCT]-(:OrderItem)-[:PART_OF]->(o:Order)
MATCH (o)<-[:PART_OF]-(:OrderItem)-[:FOR_PRODUCT]->(:Product)-[:IN_CATEGORY]->(b:Category)
WHERE a.category_name < b.category_name AND o.purchased_at >= $start AND o.purchased_at < $end
WITH DISTINCT a.category_name AS category_a, b.category_name AS category_b, o.order_id AS order_id
RETURN category_a, category_b, count(*) AS shared_orders
ORDER BY category_a, category_b;
