"""Shared entity vocabulary, keys and edges for the two implementations."""

# Insertion order is a topological order of foreign-key dependencies.
ENTITIES = {
    "customers": ("Customer", ("customer_id",)),
    "customer_records": ("CustomerRecord", ("record_id",)),
    "categories": ("Category", ("category_name",)),
    "products": ("Product", ("product_id",)),
    "sellers": ("Seller", ("seller_id",)),
    "orders": ("Order", ("order_id",)),
    "order_items": ("OrderItem", ("order_id", "item_number")),
    "payments": ("Payment", ("order_id", "payment_sequence")),
    "reviews": ("Review", ("review_record_id",)),
}

# child table, FK column, parent table, parent key, graph relationship.
# Every graph edge is directed from the referencing record to its parent.
REFERENCES = [
    ("customer_records", "customer_id", "customers", "customer_id", "IDENTIFIES"),
    ("products", "category_name", "categories", "category_name", "IN_CATEGORY"),
    ("orders", "record_id", "customer_records", "record_id", "PLACED_BY"),
    ("order_items", "order_id", "orders", "order_id", "PART_OF"),
    ("order_items", "product_id", "products", "product_id", "FOR_PRODUCT"),
    ("order_items", "seller_id", "sellers", "seller_id", "SOLD_BY"),
    ("payments", "order_id", "orders", "order_id", "PAYS"),
    ("reviews", "order_id", "orders", "order_id", "REVIEWS"),
]
