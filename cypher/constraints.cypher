// Aggregate without a grouping key first, so zero input still emits a zero-violation row.
MATCH (n:Customer) WITH n.customer_id AS customer_id, count(*) AS n WITH coalesce(sum(CASE WHEN customer_id IS NULL OR customer_id = '' THEN n ELSE n-1 END),0) AS violations RETURN 'C1:customers' AS rule, violations
UNION ALL
MATCH (n:CustomerRecord) WITH n.record_id AS record_id, count(*) AS n WITH coalesce(sum(CASE WHEN record_id IS NULL OR record_id = '' THEN n ELSE n-1 END),0) AS violations RETURN 'C1:customer_records' AS rule, violations
UNION ALL
MATCH (n:Category) WITH n.category_name AS category_name, count(*) AS n WITH coalesce(sum(CASE WHEN category_name IS NULL OR category_name = '' THEN n ELSE n-1 END),0) AS violations RETURN 'C1:categories' AS rule, violations
UNION ALL
MATCH (n:Product) WITH n.product_id AS product_id, count(*) AS n WITH coalesce(sum(CASE WHEN product_id IS NULL OR product_id = '' THEN n ELSE n-1 END),0) AS violations RETURN 'C1:products' AS rule, violations
UNION ALL
MATCH (n:Seller) WITH n.seller_id AS seller_id, count(*) AS n WITH coalesce(sum(CASE WHEN seller_id IS NULL OR seller_id = '' THEN n ELSE n-1 END),0) AS violations RETURN 'C1:sellers' AS rule, violations
UNION ALL
MATCH (n:Order) WITH n.order_id AS order_id, count(*) AS n WITH coalesce(sum(CASE WHEN order_id IS NULL OR order_id = '' THEN n ELSE n-1 END),0) AS violations RETURN 'C1:orders' AS rule, violations
UNION ALL
MATCH (n:OrderItem) WITH n.order_id AS order_id, n.item_number AS item_number, count(*) AS n WITH coalesce(sum(CASE WHEN order_id IS NULL OR order_id = '' OR item_number IS NULL THEN n ELSE n-1 END),0) AS violations RETURN 'C1:order_items' AS rule, violations
UNION ALL
MATCH (n:Payment) WITH n.order_id AS order_id, n.payment_sequence AS payment_sequence, count(*) AS n WITH coalesce(sum(CASE WHEN order_id IS NULL OR order_id = '' OR payment_sequence IS NULL THEN n ELSE n-1 END),0) AS violations RETURN 'C1:payments' AS rule, violations
UNION ALL
MATCH (n:Review) WITH n.review_record_id AS review_record_id, count(*) AS n WITH coalesce(sum(CASE WHEN review_record_id IS NULL OR review_record_id = '' THEN n ELSE n-1 END),0) AS violations RETURN 'C1:reviews' AS rule, violations
UNION ALL
MATCH (c:CustomerRecord) OPTIONAL MATCH (c)-[r:IDENTIFIES]->(p) WITH c, count(r) AS edges, collect(CASE WHEN p:Customer THEN p.customer_id ELSE null END) AS targets WITH coalesce(sum(CASE WHEN edges=1 AND size(targets)=1 AND targets[0]=c.customer_id THEN 0 ELSE 1 END),0) AS violations RETURN 'C2:customer_records.customer_id' AS rule, violations
UNION ALL
MATCH (c:Product) OPTIONAL MATCH (c)-[r:IN_CATEGORY]->(p) WITH c, count(r) AS edges, collect(CASE WHEN p:Category THEN p.category_name ELSE null END) AS targets WITH coalesce(sum(CASE WHEN c.category_name IS NULL AND edges=0 THEN 0 WHEN edges=1 AND size(targets)=1 AND targets[0]=c.category_name THEN 0 ELSE 1 END),0) AS violations RETURN 'C2:products.category_name' AS rule, violations
UNION ALL
MATCH (c:Order) OPTIONAL MATCH (c)-[r:PLACED_BY]->(p) WITH c, count(r) AS edges, collect(CASE WHEN p:CustomerRecord THEN p.record_id ELSE null END) AS targets WITH coalesce(sum(CASE WHEN edges=1 AND size(targets)=1 AND targets[0]=c.record_id THEN 0 ELSE 1 END),0) AS violations RETURN 'C2:orders.record_id' AS rule, violations
UNION ALL
MATCH (c:OrderItem) OPTIONAL MATCH (c)-[r:PART_OF]->(p) WITH c, count(r) AS edges, collect(CASE WHEN p:Order THEN p.order_id ELSE null END) AS targets WITH coalesce(sum(CASE WHEN edges=1 AND size(targets)=1 AND targets[0]=c.order_id THEN 0 ELSE 1 END),0) AS violations RETURN 'C2:order_items.order_id' AS rule, violations
UNION ALL
MATCH (c:OrderItem) OPTIONAL MATCH (c)-[r:FOR_PRODUCT]->(p) WITH c, count(r) AS edges, collect(CASE WHEN p:Product THEN p.product_id ELSE null END) AS targets WITH coalesce(sum(CASE WHEN edges=1 AND size(targets)=1 AND targets[0]=c.product_id THEN 0 ELSE 1 END),0) AS violations RETURN 'C2:order_items.product_id' AS rule, violations
UNION ALL
MATCH (c:OrderItem) OPTIONAL MATCH (c)-[r:SOLD_BY]->(p) WITH c, count(r) AS edges, collect(CASE WHEN p:Seller THEN p.seller_id ELSE null END) AS targets WITH coalesce(sum(CASE WHEN edges=1 AND size(targets)=1 AND targets[0]=c.seller_id THEN 0 ELSE 1 END),0) AS violations RETURN 'C2:order_items.seller_id' AS rule, violations
UNION ALL
MATCH (c:Payment) OPTIONAL MATCH (c)-[r:PAYS]->(p) WITH c, count(r) AS edges, collect(CASE WHEN p:Order THEN p.order_id ELSE null END) AS targets WITH coalesce(sum(CASE WHEN edges=1 AND size(targets)=1 AND targets[0]=c.order_id THEN 0 ELSE 1 END),0) AS violations RETURN 'C2:payments.order_id' AS rule, violations
UNION ALL
MATCH (c:Review) OPTIONAL MATCH (c)-[r:REVIEWS]->(p) WITH c, count(r) AS edges, collect(CASE WHEN p:Order THEN p.order_id ELSE null END) AS targets WITH coalesce(sum(CASE WHEN edges=1 AND size(targets)=1 AND targets[0]=c.order_id THEN 0 ELSE 1 END),0) AS violations RETURN 'C2:reviews.order_id' AS rule, violations
UNION ALL
MATCH (n:OrderItem) WHERE CASE WHEN n.price_cents IS :: INTEGER NOT NULL AND n.freight_cents IS :: INTEGER NOT NULL THEN n.price_cents < 0 OR n.freight_cents < 0 ELSE true END WITH count(*) AS violations RETURN 'C3:order_items' AS rule, violations
UNION ALL
MATCH (n:Payment) WHERE CASE WHEN n.amount_cents IS :: INTEGER NOT NULL THEN n.amount_cents < 0 ELSE true END WITH count(*) AS violations RETURN 'C3:payments' AS rule, violations
UNION ALL
MATCH (n:Review) WHERE CASE WHEN n.score IS :: INTEGER NOT NULL THEN n.score < 1 OR n.score > 5 ELSE true END WITH count(*) AS violations RETURN 'C4:reviews' AS rule, violations
UNION ALL
MATCH (n:OrderItem) WHERE CASE WHEN n.item_number IS :: INTEGER NOT NULL THEN n.item_number < 1 ELSE true END WITH count(*) AS violations RETURN 'C5:order_items' AS rule, violations
UNION ALL
MATCH (n:Payment) WHERE CASE WHEN n.payment_sequence IS :: INTEGER NOT NULL THEN n.payment_sequence < 1 ELSE true END WITH count(*) AS violations RETURN 'C5:payments' AS rule, violations;
