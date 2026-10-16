"""Independent Python set/count definitions for the five business questions.

No SQL, Cypher or database connection is used. These expectations complement
cross-engine comparison; the exported small real sample supports human review.
"""
from collections import Counter, defaultdict
from itertools import combinations

from .model import ENTITIES, REFERENCES


QUERY_IDS = ("Q1", "Q2", "Q3", "Q4", "Q5", "constraints")


def evaluate(tables, params):
    owners = {r["record_id"]: r["customer_id"] for r in tables["customer_records"]}
    orders = {r["order_id"]: r for r in tables["orders"]
              if params["start"] <= r["purchased_at"] < params["end"]}
    paid = Counter()
    for row in tables["payments"]:
        paid[row["order_id"]] += row["amount_cents"]
    reviewed, low = set(), set()
    for row in tables["reviews"]:
        reviewed.add(row["order_id"])
        if row["score"] <= params["low_score"]:
            low.add(row["order_id"])
    product_categories = {r["product_id"]: r["category_name"] for r in tables["products"]}
    sellers, categories = defaultdict(set), defaultdict(set)
    for row in tables["order_items"]:
        if row["order_id"] in orders:
            sellers[row["order_id"]].add(row["seller_id"])
            category = product_categories[row["product_id"]]
            if category is not None:
                categories[row["order_id"]].add(category)
    q1, totals, delivery = [], defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for oid, order in orders.items():
        customer = owners[order["record_id"]]
        if customer == params["customer_id"]:
            q1.append(dict(order_id=oid, status=order["status"], purchased_at=order["purchased_at"],
                           payment_total_cents=paid[oid]))
        totals[customer][0] += 1
        totals[customer][1] += paid[oid]
        if oid in reviewed and order["delivered_at"] and order["estimated_at"]:
            group = "late" if order["delivered_at"] > order["estimated_at"] else "on_time"
            delivery[group][0] += 1
            delivery[group][1] += oid in low
    flagged = set()
    for oid in low & orders.keys():
        flagged.update(sellers[oid])
    pairs = {(seller, owners[order["record_id"]]) for oid, order in orders.items()
             for seller in sellers[oid] if seller in flagged}
    shared = Counter(pair for values in categories.values() for pair in combinations(sorted(values), 2))
    rules = ([f"C1:{table}" for table in ENTITIES]
             + [f"C2:{child}.{fk}" for child, fk, *_ in REFERENCES]
             + ["C3:order_items", "C3:payments", "C4:reviews", "C5:order_items", "C5:payments"])
    return {
        "Q1": sorted(q1, key=lambda r: r["order_id"]),
        "Q2": [dict(customer_id=c, order_count=n, payment_total_cents=amount)
               for c, (n, amount) in sorted(totals.items())],
        "Q3": [dict(delivery_group=g, reviewed_orders=n, low_rated_orders=count)
               for g, (n, count) in sorted(delivery.items())],
        "Q4": [dict(seller_id=s, customer_id=c) for s, c in sorted(pairs)],
        "Q5": [dict(category_a=a, category_b=b, shared_orders=n) for (a, b), n in sorted(shared.items())],
        "constraints": [dict(rule=rule, violations=0) for rule in sorted(rules)],
    }


def sample(tables, params):
    """Select source-backed edge cases, then take their complete parent closure."""
    payments = Counter(r["order_id"] for r in tables["payments"])
    reviews = Counter(r["order_id"] for r in tables["reviews"])
    categories = {r["product_id"]: r["category_name"] for r in tables["products"]}
    by_order = defaultdict(set)
    missing_category = set()
    for row in tables["order_items"]:
        category = categories[row["product_id"]]
        if category:
            by_order[row["order_id"]].add(category)
        else:
            missing_category.add(row["order_id"])
    owners = {r["record_id"]: r["customer_id"] for r in tables["customer_records"]}
    selected, cases = set(), {}
    for order in sorted(tables["orders"], key=lambda r: r["order_id"]):
        oid = order["order_id"]
        flags = {"multiple_payments": payments[oid] > 1, "multiple_reviews": reviews[oid] > 1,
                 "no_payment": payments[oid] == 0, "multiple_categories": len(by_order[oid]) > 1,
                 "unknown_category": oid in missing_category,
                 "selected_customer": owners[order["record_id"]] == params["customer_id"]}
        if order["delivered_at"] and order["estimated_at"] and reviews[oid]:
            flags["late" if order["delivered_at"] > order["estimated_at"] else "on_time"] = True
        for name, matches in flags.items():
            if matches and name not in cases:
                cases[name] = oid
                selected.add(oid)
    result = {table: [] for table in ENTITIES}
    result["orders"] = [r for r in tables["orders"] if r["order_id"] in selected]
    records = {r["record_id"] for r in result["orders"]}
    result["customer_records"] = [r for r in tables["customer_records"] if r["record_id"] in records]
    customers = {r["customer_id"] for r in result["customer_records"]}
    result["customers"] = [r for r in tables["customers"] if r["customer_id"] in customers]
    for table in ("order_items", "payments", "reviews"):
        result[table] = [r for r in tables[table] if r["order_id"] in selected]
    products = {r["product_id"] for r in result["order_items"]}
    sellers = {r["seller_id"] for r in result["order_items"]}
    result["products"] = [r for r in tables["products"] if r["product_id"] in products]
    result["sellers"] = [r for r in tables["sellers"] if r["seller_id"] in sellers]
    category_names = {r["category_name"] for r in result["products"]}
    result["categories"] = [r for r in tables["categories"] if r["category_name"] in category_names]
    arithmetic = []
    for order in sorted(result["orders"], key=lambda r: r["order_id"]):
        oid = order["order_id"]
        amounts = [r["amount_cents"] for r in result["payments"] if r["order_id"] == oid]
        scores = [r["score"] for r in result["reviews"] if r["order_id"] == oid]
        arithmetic.append(dict(order_id=oid, payment_amounts_cents=amounts,
                               payment_sum_cents=sum(amounts), review_scores=scores,
                               low_rated=any(s <= params["low_score"] for s in scores),
                               categories=sorted(by_order[oid]),
                               category_pairs=list(combinations(sorted(by_order[oid]), 2))))
    return dict(cases=cases, tables=result, arithmetic=arithmetic,
                expected_within_sample=evaluate(result, params),
                scope="Parent-complete real subset; subset aggregates are not full-dataset expectations")
