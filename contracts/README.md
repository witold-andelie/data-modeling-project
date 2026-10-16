# Data-mining course integration boundary v1.0

The database project owns raw-source provenance, normalized business data,
stable business IDs, feature extraction semantics and input/output validation.
The other course owns exploration, algorithms, training, evaluation and model
interpretation. No machine-learning dependency is required here.

## Export: customer feature snapshot

Command: `c360 export-features --start ... --end ... --out ...`.
Schema: `features.schema.json`. One row per customer having a purchase in the
left-closed/right-open window. Orders include all source statuses.

| Field | Meaning |
|---|---|
| customer_id | Source customer_unique_id, not order-associated customer_id |
| order_count | Number of orders purchased in the window |
| payment_total_cents | Sum of payment records linked to those orders, BRL cents |
| last_purchase_at | Maximum purchase timestamp inside the window |
| recency_days | Cutoff calendar date minus last purchase calendar date |

`dataset_id` identifies the full prepared snapshot. `feature_export_id` is
SHA-256 of canonical JSON excluding the hash field: UTF-8, sorted keys,
ensure_ascii=False, separators comma/colon without spaces. The window and
population definition are part of the hash.

This is a retrospective extract from a historical snapshot. Filtering order
purchase times does not reconstruct when each payment became known. The export
therefore declares `temporal_semantics=retrospective_snapshot` and
`point_in_time_safe=false`. A predictive task must define its own observation
time, labels, censoring rules and information-availability policy. This project
does not claim to solve data leakage for that future task.

## Return: external customer annotations

Schema: `results.schema.json`. Required metadata: schema version, feature export
hash, model identifier/version, timezone-qualified generation timestamp.
Assignments contain customer_id, a nonempty label and optional score in [0,1].
The optional score has model-defined meaning, not automatically a calibrated
probability. A subset of exported customers may be returned; duplicate or
unknown customer IDs are rejected.

`c360 validate-results` checks the file against the actual referenced feature
snapshot without writing business data. Persisting derived results is a future
adapter task. An immutable annotation key should include model version,
feature-export hash and customer ID. Never replace source attributes with an
algorithm's inferred labels.

The schemas describe the exchange format; the standard-library runtime also
checks provenance equality, membership and uniqueness across rows. This is a
file contract, not an HTTP endpoint or a deployed model service.
