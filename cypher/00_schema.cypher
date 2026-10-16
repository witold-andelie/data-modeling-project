// Neo4j Community: uniqueness is native; required properties, ranges and
// relationship cardinalities also need loader validation and audit queries.
CREATE CONSTRAINT snapshot_id IF NOT EXISTS FOR (n:ProjectSnapshot) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT customers_key IF NOT EXISTS FOR (n:Customer) REQUIRE n.customer_id IS UNIQUE;
CREATE CONSTRAINT customer_records_key IF NOT EXISTS FOR (n:CustomerRecord) REQUIRE n.record_id IS UNIQUE;
CREATE CONSTRAINT categories_key IF NOT EXISTS FOR (n:Category) REQUIRE n.category_name IS UNIQUE;
CREATE CONSTRAINT products_key IF NOT EXISTS FOR (n:Product) REQUIRE n.product_id IS UNIQUE;
CREATE CONSTRAINT sellers_key IF NOT EXISTS FOR (n:Seller) REQUIRE n.seller_id IS UNIQUE;
CREATE CONSTRAINT orders_key IF NOT EXISTS FOR (n:Order) REQUIRE n.order_id IS UNIQUE;
CREATE CONSTRAINT order_items_key IF NOT EXISTS FOR (n:OrderItem) REQUIRE (n.order_id, n.item_number) IS UNIQUE;
CREATE CONSTRAINT payments_key IF NOT EXISTS FOR (n:Payment) REQUIRE (n.order_id, n.payment_sequence) IS UNIQUE;
CREATE CONSTRAINT reviews_key IF NOT EXISTS FOR (n:Review) REQUIRE n.review_record_id IS UNIQUE;
CREATE INDEX orders_purchased IF NOT EXISTS FOR (n:Order) ON (n.purchased_at);
