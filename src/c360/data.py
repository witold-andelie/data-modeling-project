"""Strict source preparation. Source CSVs are never edited or silently repaired."""
import csv
import hashlib
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .model import ENTITIES, REFERENCES

FILES = {
    "customer_records": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
}

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def cents(value):
    try:
        amount = Decimal(value) * 100
        if not amount.is_finite() or amount != amount.to_integral_value():
            raise ValueError("Amount must have at most two decimal places")
        result = int(amount)
        if result < 0:
            raise ValueError("Negative amount")
        return result
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"Invalid money value: {value!r}") from exc

def optional_int(value):
    if not value:
        return None
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Expected an integral value: {value!r}") from exc
    if not number.is_finite() or number != number.to_integral_value():
        raise ValueError(f"Expected an integral value: {value!r}")
    return int(number)

def timestamp(value):
    if not value:
        return None
    # Olist supplies naive timestamps. Do not invent a timezone.
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").isoformat(timespec="seconds")

def normalize(table, r, line):
    if table == "customer_records":
        return dict(record_id=r["customer_id"], customer_id=r["customer_unique_id"],
                    zip_prefix=r["customer_zip_code_prefix"], city=r["customer_city"], state=r["customer_state"])
    if table == "products":
        return dict(product_id=r["product_id"], category_name=r["product_category_name"] or None,
                    weight_g=optional_int(r["product_weight_g"]))
    if table == "sellers":
        return dict(seller_id=r["seller_id"], zip_prefix=r["seller_zip_code_prefix"],
                    city=r["seller_city"], state=r["seller_state"])
    if table == "orders":
        if not r["order_purchase_timestamp"]:
            raise ValueError("Order purchase timestamp is required")
        return dict(order_id=r["order_id"], record_id=r["customer_id"], status=r["order_status"],
                    purchased_at=timestamp(r["order_purchase_timestamp"]),
                    approved_at=timestamp(r["order_approved_at"]),
                    delivered_at=timestamp(r["order_delivered_customer_date"]),
                    estimated_at=timestamp(r["order_estimated_delivery_date"]))
    if table == "order_items":
        return dict(order_id=r["order_id"], item_number=int(r["order_item_id"]),
                    product_id=r["product_id"], seller_id=r["seller_id"],
                    price_cents=cents(r["price"]), freight_cents=cents(r["freight_value"]))
    if table == "payments":
        return dict(order_id=r["order_id"], payment_sequence=int(r["payment_sequential"]),
                    payment_type=r["payment_type"], installments=int(r["payment_installments"]),
                    amount_cents=cents(r["payment_value"]))
    if table == "reviews":
        # Source review_id is not assumed globally unique. Preserve every source row.
        return dict(review_record_id=f"review-row-{line}", source_review_id=r["review_id"],
                    order_id=r["order_id"], score=int(r["review_score"]),
                    created_at=timestamp(r["review_creation_date"]))
    raise ValueError(table)

def violations(tables, minimum=0):
    issues = []
    def issue(rule, table, key, detail):
        issues.append(dict(rule=rule, table=table, key=key, detail=detail))
    for table, (_, keys) in ENTITIES.items():
        seen = set()
        rows = tables.get(table, [])
        if len(rows) < minimum:
            issue("coverage", table, None, f"Requires {minimum} rows; found {len(rows)}")
        for r in rows:
            key = tuple(r.get(k) for k in keys)
            if any(v is None or v == "" for v in key) or key in seen:
                issue("C1", table, list(key), "Missing or duplicate primary key")
            seen.add(key)
    for child, fk, parent, pk, _ in REFERENCES:
        valid = {r[pk] for r in tables.get(parent, [])}
        for r in tables.get(child, []):
            if child == "products" and r[fk] is None:
                continue
            if r[fk] not in valid:
                issue("C2", child, r[fk], f"Missing {parent}.{pk}")
    for table, columns in [("order_items", ("price_cents", "freight_cents")),
                           ("payments", ("amount_cents",))]:
        for r in tables.get(table, []):
            if any(type(r[c]) is not int or r[c] < 0 for c in columns):
                issue("C3", table, r["order_id"], "Amount must be nonnegative integer cents")
    for r in tables.get("reviews", []):
        if type(r["score"]) is not int or not 1 <= r["score"] <= 5:
            issue("C4", "reviews", r["review_record_id"], "Score must be integer 1..5")
    for table, col in [("order_items", "item_number"), ("payments", "payment_sequence")]:
        for r in tables.get(table, []):
            if type(r[col]) is not int or r[col] < 1:
                issue("C5", table, r["order_id"], "Sequence number must be positive")
    return issues

def prepare(raw_dir, out_dir):
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    missing = [name for name in FILES.values() if not (raw_dir / name).is_file()]
    if missing:
        write_json(out_dir / "quality.json", dict(ready=False, missing_files=missing))
        raise ValueError("Missing original Olist files: " + ", ".join(missing))
    tables = {name: [] for name in ENTITIES}
    sources, errors = {}, []
    for table, filename in FILES.items():
        path = raw_dir / filename
        sources[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for line, row in enumerate(csv.DictReader(stream), 2):
                try:
                    tables[table].append(normalize(table, row, line))
                except (KeyError, ValueError, TypeError) as exc:
                    errors.append(dict(file=filename, line=line, detail=str(exc)))
    tables["customers"] = [{"customer_id": value} for value in sorted(
        {r["customer_id"] for r in tables["customer_records"]})]
    tables["categories"] = [{"category_name": value} for value in sorted(
        {r["category_name"] for r in tables["products"] if r["category_name"] is not None})]
    errors.extend(violations(tables, minimum=5))
    report = dict(source_sha256=sources, counts={k: len(v) for k, v in tables.items()},
                  issues=errors, ready=not errors)
    write_json(out_dir / "quality.json", report)
    if errors:
        raise ValueError(f"Preparation blocked by {len(errors)} issues; inspect {out_dir / 'quality.json'}")
    payload = dict(schema_version="1.0", source_sha256=sources, tables=tables)
    payload["dataset_id"] = digest(payload)
    write_json(out_dir / "dataset.json", payload)
    return report

def load_dataset(path):
    data = read_json(path)
    quality_path = Path(path).with_name("quality.json")
    if quality_path.exists():
        quality = read_json(quality_path)
        if not quality.get("ready") or quality.get("source_sha256") != data.get("source_sha256"):
            raise ValueError("Latest preparation failed or source manifest differs; inspect quality.json")
    if data.get("schema_version") != "1.0":
        raise ValueError("Unsupported dataset schema")
    expected = digest({k: v for k, v in data.items() if k != "dataset_id"})
    if data.get("dataset_id") != expected:
        raise ValueError("Dataset hash mismatch")
    issues = violations(data["tables"])
    if issues:
        raise ValueError(f"Dataset validation failed: {issues[:3]}")
    return data
