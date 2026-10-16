MATCH (r:Review)-[:REVIEWS]->(seed:Order)<-[:PART_OF]-(:OrderItem)-[:SOLD_BY]->(s:Seller)
WHERE r.score <= $low_score AND seed.purchased_at >= $start AND seed.purchased_at < $end
WITH DISTINCT s
MATCH (s)<-[:SOLD_BY]-(:OrderItem)-[:PART_OF]->(o:Order)-[:PLACED_BY]->(:CustomerRecord)-[:IDENTIFIES]->(c:Customer)
WHERE o.purchased_at >= $start AND o.purchased_at < $end
RETURN DISTINCT s.seller_id AS seller_id, c.customer_id AS customer_id
ORDER BY seller_id, customer_id;
