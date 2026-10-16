"""Versioned file boundary to the separate data-mining course. No training code."""
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import math

from .data import digest, write_json

def export_features(dataset, start, end, output):
    begin, cutoff = datetime.fromisoformat(start), datetime.fromisoformat(end)
    if begin.tzinfo or cutoff.tzinfo or begin >= cutoff:
        raise ValueError("Use naive ISO source-local timestamps with start < end")
    start, end = begin.isoformat(timespec="seconds"), cutoff.isoformat(timespec="seconds")
    t = dataset["tables"]
    identities = {r["record_id"]: r["customer_id"] for r in t["customer_records"]}
    # Aggregate payments before joining orders: prevents item/payment fan-out.
    payments = defaultdict(int)
    for p in t["payments"]:
        payments[p["order_id"]] += p["amount_cents"]
    rows = {}
    for order in t["orders"]:
        purchased = datetime.fromisoformat(order["purchased_at"])
        if not begin <= purchased < cutoff:
            continue
        customer = identities[order["record_id"]]
        row = rows.setdefault(customer, dict(customer_id=customer, order_count=0,
            payment_total_cents=0, last_purchase_at=order["purchased_at"]))
        row["order_count"] += 1
        row["payment_total_cents"] += payments[order["order_id"]]
        row["last_purchase_at"] = max(row["last_purchase_at"], order["purchased_at"])
    for row in rows.values():
        row["recency_days"] = (cutoff.date() - datetime.fromisoformat(row["last_purchase_at"]).date()).days
    result = dict(schema_version="1.0", dataset_id=dataset["dataset_id"],
        window_start=start, window_end_exclusive=end, currency="BRL", money_unit="cent",
        temporal_semantics="retrospective_snapshot", point_in_time_safe=False,
        population="customers with at least one purchase in the window; all source order statuses",
        rows=[rows[key] for key in sorted(rows)])
    result["feature_export_id"] = digest(result)
    write_json(output, result)
    return result

def validate_results(result, features):
    """Accept customer annotations as external derived data, never source facts."""
    if not isinstance(result, dict) or not isinstance(features, dict):
        raise ValueError("Result and feature files must be JSON objects")
    feature_id = digest({k: v for k, v in features.items() if k != "feature_export_id"})
    if feature_id != features.get("feature_export_id"):
        raise ValueError("Feature export hash mismatch")
    for field in ("model_id", "model_version", "generated_at", "feature_export_id"):
        if not isinstance(result.get(field), str) or not result[field].strip():
            raise ValueError(f"Missing string: {field}")
    if result.get("schema_version") != "1.0":
        raise ValueError("Unsupported result schema")
    if result["feature_export_id"] != features["feature_export_id"]:
        raise ValueError("Results refer to a different feature snapshot")
    if datetime.fromisoformat(result["generated_at"].replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("generated_at must include a timezone")
    if not isinstance(result.get("assignments"), list) or not result["assignments"]:
        raise ValueError("assignments must be a nonempty array")
    population = {r["customer_id"] for r in features["rows"]}
    seen = set()
    for row in result["assignments"]:
        if not isinstance(row, dict):
            raise ValueError("Each assignment must be an object")
        customer = row.get("customer_id")
        if not isinstance(customer, str) or customer not in population or customer in seen:
            raise ValueError(f"Unknown or duplicate customer: {customer}")
        seen.add(customer)
        if not isinstance(row.get("label"), str) or not row["label"].strip():
            raise ValueError("Each assignment needs a nonempty label")
        score = row.get("score")
        if score is not None and (type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1):
            raise ValueError("Optional score must be finite and between 0 and 1")
    return dict(valid=True, accepted_assignments=len(seen), feature_export_id=feature_id,
                note="Validated only; no write to source databases")
