"""Check fixed real-source arithmetic and its database outcomes, one engine at a time."""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from c360 import data, database


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", required=True, choices=["mysql", "neo4j"])
    parser.add_argument("--out", default="artifacts/database-verification")
    args = parser.parse_args()
    spec = data.read_json(ROOT / "config/real-sample-assertions.json")
    small = data.read_json(ROOT / "artifacts/reference/real-sample.json")
    params = database.validate_parameters(data.read_json(ROOT / "config/query-parameters.json"))
    if small["dataset_id"] != spec["dataset_id"] or params != small["parameters"]:
        raise ValueError("Real assertions apply only to the recorded source snapshot and parameters")
    t = small["tables"]
    checks = []
    def check(name, matches):
        checks.append(dict(case=name, passed=bool(matches)))
    amounts = sorted(r["amount_cents"] for r in t["payments"] if r["order_id"] == spec["multiple_payment_order"])
    check("integer-cent arithmetic", amounts == spec["payment_parts_cents"] and sum(amounts) == spec["payment_sum_cents"])
    check("no payment retained", not any(r["order_id"] == spec["no_payment_order"] for r in t["payments"]))
    check("both review rows retained", sorted(r["score"] for r in t["reviews"] if r["order_id"] == spec["multiple_review_order"]) == spec["review_scores"])
    products = {r["product_id"]: r["category_name"] for r in t["products"]}
    categories = sorted({products[r["product_id"]] for r in t["order_items"] if r["order_id"] == spec["category_pair_order"]})
    check("known category pair", categories == spec["category_pair"])
    records = {r["record_id"]: r["customer_id"] for r in t["customer_records"]}
    orders = {r["order_id"]: r for r in t["orders"]}
    for name, oid, expected in [("split payments", spec["multiple_payment_order"], spec["payment_sum_cents"]),
                                 ("zero payments", spec["no_payment_order"], 0)]:
        customer = records[orders[oid]["record_id"]]
        result = database.query(args.engine, "Q1", dict(params, customer_id=customer))
        if result["dataset_id"] != spec["dataset_id"]:
            raise ValueError("Database source snapshot differs")
        data.write_json(Path(args.out) / f"{args.engine}-real-{oid}.json", result)
        matches = [r for r in result["rows"] if r["order_id"] == oid]
        check(name, len(matches) == 1 and matches[0]["payment_total_cents"] == expected)
    q1 = data.read_json(Path(args.out) / f"{args.engine}-Q1.json")
    q2 = data.read_json(Path(args.out) / f"{args.engine}-Q2.json")
    for result in (q1, q2):
        if result["dataset_id"] != spec["dataset_id"] or result["parameters"] != params:
            raise ValueError("Saved result provenance differs")
    check("customer order amounts", {r["order_id"]: r["payment_total_cents"] for r in q1["rows"]} == spec["customer_orders"])
    customer = next(r for r in q2["rows"] if r["customer_id"] == spec["customer_id"])
    check("customer identity merge", customer["order_count"] == spec["customer_order_count"]
          and customer["payment_total_cents"] == spec["customer_payment_total_cents"])
    check("at least five real instances per class", all(len(rows) >= 5 for rows in t.values()))
    summary = dict(engine=args.engine, dataset_id=spec["dataset_id"], checks=checks,
                   executed_at=datetime.now(timezone.utc).isoformat(), passed=all(c["passed"] for c in checks))
    data.write_json(Path(args.out) / f"{args.engine}-real-cases.json", summary)
    print(summary)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
