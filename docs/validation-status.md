# Validation status — 2026-10-16 (Europe/Budapest)

The database implementation phase is verified on real data: MySQL, Neo4j and
the independent Python reference agree on all five queries and all 22 audit
results. Both task databases were stopped gracefully after verification, with
volumes preserved. Report prose/PDF and genuine teacher consultations remain
separate outstanding coursework deliverables. Machine-readable gate:
`artifacts/delivery-status.json`.

## Passed

- 15 standard-library unit tests using explicitly synthetic fixtures, including
  independent-reference fan-out, identity and missing-payment/window cases.
- Python syntax, expected query pairs and model-source inventory checks.
- CLI help execution.
- Docker Compose configuration validation using `.env.example` (no containers started).
- All seven SQL files parsed as MySQL with sqlglot 30.12.0. This is a static
  parser check, not execution against MySQL.
- Both exchange JSON Schema definitions validated with jsonschema.
- Seven original CSV SHA-256 hashes rechecked against dataset
  `06e60f81265902ca3e7e2620dbb15c53a49301c1631a120ad160e6abbb364ff3`.
  Nine classes contain 96,096 customers; 99,441 source customer records;
  73 categories; 32,951 products; 3,095 sellers; 99,441 orders; 112,650 items;
  103,886 payment records; 100,000 reviews. No rows were silently removed.
- Parent-complete real subset with 7–11 objects in each of the nine classes,
  including split payments, missing payment, multiple reviews, late/on-time
  delivery and unknown category. Raw-CSV profiling and normalization argument
  are available in `artifacts/reference/` and `docs/normalization.md`.
- MySQL 8.4.11 full load, immutable same-snapshot reload (`already_loaded`),
  and all five queries agree with independent Python expectations.
- MySQL Q1/Q2/Q3/Q4/Q5 row counts: 2 / 96,096 / 2 / 94,806 / 243.
  All 22 C1–C5 audit rows have zero violations. Five invalid-write cases were
  rejected natively (1062 / 1452 / 3819 / 3819 / 3819); transactions rolled
  back and the subsequent audit remained clean. Nine fixed real-case checks passed.
- MySQL plans, driver version 9.7.0 and one observed query timing are archived.
  These timings include connections and are not a controlled benchmark.
- Neo4j 5.26.32 with driver 5.28.8 completed the same full snapshot using batches
  of 500 rows for both nodes and relationships. Counts match every source class.
  Reload returns `already_loaded` without replacing the snapshot.
- Neo4j Q1/Q2/Q3/Q4/Q5 return the same 2 / 96,096 / 2 / 94,806 / 243 rows.
  All 22 audit rows have zero violations. Identity duplication was rejected
  natively; C2–C5 invalid writes each produced exactly one audit violation inside
  a transaction. Every transaction rolled back, and the subsequent audit was clean.
  All nine fixed real-case checks passed. Native plans and one observed timing
  per query are archived, with no controlled performance ranking claimed.
- `scripts/verify_databases.py --compare-only` passed all six comparisons among
  both engines and Python, using identical dataset IDs and parameters. Evidence:
  `artifacts/database-verification/summary.json` and `compare-*.json`.
- Actual MySQL container memory and memory+swap limits are both 536,870,912
  bytes, verified by Docker inspect. Image digest and limits are archived under
  `artifacts/runtime/mysql.json`. Observed post-verification usage was about
  417MiB/512MiB; this is not a measured peak.
- Neo4j's actual memory and memory+swap limits are both 1,073,741,824 bytes,
  verified by Docker inspect and archived in `artifacts/runtime/neo4j.json`.
  Observed post-verification usage was about 864MiB/1GiB, not a measured peak.
  Final inspect shows both databases exited with code 0 and OOMKilled=false;
  no data volumes were deleted. `artifacts/runtime/final-containers.json` records
  the final inspected state.
- Three UML PNGs rendered using PlantUML 1.2026.8 with a 256MiB Java heap and
  visually inspected. Explicit `{field}` annotations prevent CHAR/VARCHAR fields
  from disappearing under `hide methods`. Manifest records current source hashes.
- Real feature export: 96,096 customers, schema-valid, feature hash
  `d55b23a9b494069139be5a6da065da6752aaf0020df1e65438b0601981963f92`.
  It explicitly declares retrospective semantics and point_in_time_safe=false.

Reproduce and archive the checks using `py -3 scripts/verify_local.py`.
Machine-readable evidence: `artifacts/validation/summary.json`; detailed test
output: `artifacts/validation/unit-tests.log`. These generated artifacts are
included in the repository as lightweight evidence. Raw/prepared datasets,
full query rows, the real subset and feature exports remain local and ignored;
regenerate them before rerunning the complete delivery gate on a fresh clone.
The scripts and tests are the durable reproduction instructions.

## Pending and deferred

- Three genuine teacher consultations and terminology/category presentation review.
- Official Kaggle archive checksum remains unavailable: source CSVs came from
  the pinned public mirror documented in `docs/sources.md`. Individual hashes and
  the generic CC license text are archived; these are not an official zip checksum.
- Controlled performance experiments were not run; no engine speed ranking is claimed.
- Actual external model output belongs to the separate course. The file contract
  and tests are retained; no training, clustering, recommendation or model service.
- English report, cover metadata, source appendix and PDF rendering remain
  deferred at the user's request.

## Resolved during scaffold verification

The first test attempt could not access the environment's system temporary
directories. Tests now create isolated directories under this workspace's
ignored artifacts folder and verify their location before cleanup. The next
run passed. A failed preparation also blocks loading a stale adjacent dataset
through the latest quality report. These are engineering checks, not findings
about Olist's real data quality.

During this continuation the default MySQL C-extension connection stalled or
exited without an error message. A minimal pure-Python connection succeeded;
the adapter now uses that connector mode and a 10-second connection timeout.
Full loading, queries and constraint checks then succeeded. The underlying
C-extension/environment failure has not been diagnosed beyond this comparison.
No process was killed to resolve it.

The first live Neo4j audit returned only 17 of 22 expected rows. A minimized
native query demonstrated that a literal grouping key beside an aggregate
produces no row for empty input. All 22 audit branches now aggregate with no
grouping key in a WITH clause before attaching their rule name. The native
regression prefixes every actual audit branch with zero input: before the fix
it returned zero rows; afterwards all 22 zero-violation rows are present. This
regression runs in `scripts/probe_constraints.py` and is recorded in
`neo4j-negative-constraints.json`. Independent reference comparison rejected
the incomplete original audit, so it was never counted as a pass.

## Next acceptance step

Use `py -3 scripts/check_delivery.py` to audit the saved implementation evidence.
For a future live demonstration, use the startup script for one database at a
time. The user has authorized graceful shutdown of task-owned project databases
after checking for other active work; AGENTS.md records that policy. Teacher
review and the explicitly deferred report are the next coursework steps.
