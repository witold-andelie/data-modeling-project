# Customer 360 — Relational and Graph Database Coursework

This database coursework implements the same Customer 360 model in **MySQL and Neo4j** using real Olist e-commerce data. It verifies equivalent business queries and integrity rules, with reproducible engineering evidence suitable for an SAP IT Data & Analytics interview.

The verified snapshot contains **99,441 orders, 96,096 customers and nine entity classes**, with the original CSV SHA-256 hashes checked. Full loading, Q1–Q5, 22 audit checks per engine, five invalid-write cases per engine and real-sample assertions have passed. **Both engines agree with an independent Python reference.** The database implementation phase is complete; teacher consultations and the final report are separate deliverables. See [validation status](docs/validation-status.md) and [the delivery evidence](artifacts/delivery-status.json).

Both project containers were stopped gracefully after verification, preserving their volumes. Docker inspection confirmed actual memory limits of **512 MiB for MySQL** and **1 GiB for Neo4j**. Both exited with code 0 and were not OOM-killed. Start only one database at a time for subsequent demonstrations.

Data mining belongs to a separate course. This project provides versioned file contracts without training models or implementing clustering, classification, recommendation or association-rule algorithms. Report prose and cover metadata remain deferred at the user's request.

## Repository structure

| Path | Purpose |
|---|---|
| `docs/requirements.md` | Coursework requirements, acceptance evidence and completion status |
| `docs/design.md` | Business scope, entities, shared semantics and modeling decisions |
| `docs/normalization.md` | Candidate keys, functional dependencies, BCNF argument and higher-normal-form limits |
| `docs/queries-and-constraints.md` | English descriptions and formal definitions for Q1–Q5 and C1–C5 |
| `models/*.puml` | Conceptual, relational and graph UML sources |
| `sql/`, `cypher/` | DDL, five business queries and integrity audits |
| `src/c360/` | Data preparation, loading, result comparison and external analytics contracts |
| `contracts/` | Data-mining exchange documentation and JSON Schemas |
| `data/raw/`, `data/processed/` | Local original CSVs and the normalized snapshot with checksums |
| `artifacts/` | Validation, database, comparison and exchange evidence |
| `tests/` | Automated tests using explicitly synthetic fixtures |
| `paper/` | Seven-section report outline and evidence map; prose and cover deferred |

## Local checks without a database

Run these commands in PowerShell from the project root:

```powershell
py -3 scripts/check_framework.py
py -3 -m unittest discover -s tests -v
py -3 scripts/c360.py --help
py -3 scripts/verify_local.py
```

Core data preparation and exchange validation use only the Python standard library. Database loading requires the optional drivers:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[databases]"
Copy-Item .env.example .env
docker compose config --quiet
powershell -File scripts/start-database.ps1 -Service mysql
```

Start Docker Desktop with Linux containers before starting a database. MySQL uses host port `3307`; Neo4j Browser is available at `http://localhost:7475`, with Bolt on port `7688`. Ports bind to localhost only. Configure passwords in `.env`, which is excluded from Git. The images use MySQL 8.4 and Neo4j 5.26 Community. Record the actual image digests and driver versions after a successful run.

### Memory and database lifecycle

Run one database at a time: **MySQL has a 512 MiB hard limit; Neo4j has a 1 GiB hard limit**. Start Neo4j with `powershell -File scripts/start-database.ps1 -Service neo4j`. The startup script exits if the other database is running, preserving ongoing work. An already-running target container is inspected without being stopped or recreated.

Additional container swap is disabled. Reduce batch sizes if an operation exceeds its budget. These limits do not include Docker Desktop or WSL overhead. Configuration changes take effect when a container is created or recreated; verify the actual limits with `docker inspect` and `docker stats`.

`verify_databases.py` requires either a single engine or saved-file comparison mode. Run full-data Python work, database loading/queries and UML rendering in separate phases. The startup script records actual limits and image digests under `artifacts/runtime/`; these records describe the inspected run and do not replace future runtime checks.

## Prepare real data

Obtain the data from the [original Olist release](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), retain its license and version information, and place these original CSVs in `data/raw/`:

```text
olist_customers_dataset.csv
olist_orders_dataset.csv
olist_order_items_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
```

This implementation does not use geolocation or category-translation files. Category names retain their source values. [The source register](docs/sources.md) records the verified snapshot's acquisition and provenance limitations. Archive the applicable version and license information with any new download.

```powershell
py -3 scripts/c360.py prepare
```

Preparation writes `data/processed/quality.json` and a validated `dataset.json`. Each entity class must have at least five instances. Parsing failures, duplicate keys, unresolved references and business-rule violations block publication of the snapshot; problematic rows are not silently removed. Inspect the quality report before adopting a documented cleaning policy. Synthetic fixtures do not replace real coursework instances.

## Run the two implementations

Run the loading command for the database that is currently started. Switch databases before running the other engine's command:

```powershell
.\.venv\Scripts\python.exe scripts/c360.py load mysql
.\.venv\Scripts\python.exe scripts/c360.py load neo4j
```

Each database holds one immutable snapshot. Reloading the same completed snapshot is a no-op; a different snapshot cannot overwrite it. MySQL uses the pure-Python connector with a connection timeout. Neo4j can resume an interrupted load of the same snapshot through `MERGE`. Node and relationship transactions both use batches of 500 rows by default; reduce them with an option such as `load neo4j --batch-size 100`.

Run only one loader at a time. Do not manually modify a completed snapshot. The project provides no automatic database or volume deletion command.

Set `customer_id` in `config/query-parameters.json` to an actual unified customer ID from the prepared snapshot. Time windows are left-inclusive and right-exclusive. Timestamps retain the source's local, timezone-naive semantics.

Execute each engine's queries during its own running phase, then compare the saved files:

```powershell
.\.venv\Scripts\python.exe scripts/c360.py query mysql Q1 --out artifacts/mysql-Q1.json
.\.venv\Scripts\python.exe scripts/c360.py query neo4j Q1 --out artifacts/neo4j-Q1.json
py -3 scripts/c360.py compare artifacts/mysql-Q1.json artifacts/neo4j-Q1.json --out artifacts/compare-Q1.json
.\.venv\Scripts\python.exe scripts/c360.py query mysql constraints --out artifacts/mysql-constraints.json
.\.venv\Scripts\python.exe scripts/c360.py query neo4j constraints --out artifacts/neo4j-constraints.json
```

Repeat for Q2–Q5 and check that every audit row has `violations = 0`. The comparator requires matching snapshot IDs, query IDs and parameters. It ignores row ordering while preserving duplicate rows. **Cross-engine agreement alone does not prove correctness**: also verify business expectations against a reviewable real subset. An empty Q5 result does not automatically indicate bad data.

### Independent reference and integration verification

First generate the independent Python expectations and a real subset with complete parent references and at least five instances per class. After that offline phase, verify only the currently running database:

```powershell
py -3 scripts/build_reference.py
py -3 scripts/profile_source.py
.\.venv\Scripts\python.exe scripts/verify_databases.py --engine mysql
.\.venv\Scripts\python.exe scripts/probe_constraints.py --engine mysql
.\.venv\Scripts\python.exe scripts/verify_real_cases.py --engine mysql
```

Results, execution plans, versions, single-run timings and invalid-write evidence are archived under `artifacts/database-verification/`. The main verifier is read-only. The invalid-write script uses transactions that always roll back and audits the original snapshot afterwards.

Fixed real-data expectations are recorded in `config/real-sample-assertions.json`. They include split payments of 1,792 + 5,263 = 7,055 cents, an order without payment records, and two orders belonging to the same customer totaling 56,588 cents.

After verification, a project database started solely for this task may be stopped gracefully once no other task is using it. This lifecycle is authorized without repeated confirmation. Preserve volumes and do not stop containers used by other terminals. Switch to Neo4j, run the same checks with identical parameters, then compare saved files offline:

```powershell
.\.venv\Scripts\python.exe scripts/verify_databases.py --engine neo4j
.\.venv\Scripts\python.exe scripts/probe_constraints.py --engine neo4j
.\.venv\Scripts\python.exe scripts/verify_real_cases.py --engine neo4j
py -3 scripts/verify_databases.py --compare-only
py -3 scripts/check_delivery.py
```

Neo4j Community enforces C1 uniqueness natively; C2–C5 are checked by audits in addition to preparation and loader validation. Audit detection does not prevent arbitrary direct writes. The recorded single-run timings do not constitute a controlled performance ranking.

## Contract for the separate data-mining course

```powershell
py -3 scripts/c360.py export-features --start 2017-01-01T00:00:00 --end 2018-01-01T00:00:00 --out artifacts/customer-features.json
py -3 scripts/c360.py validate-results external-results.json --features artifacts/customer-features.json
```

The export contains basic customer aggregates such as order count, recorded payment total and latest purchase timestamp. It does not perform data mining. Olist is a historical snapshot without complete payment-availability timestamps, so the contract explicitly declares `point_in_time_safe=false`. An observation window does not establish a leakage-safe historical feature system.

External annotations must reference customers in the matching snapshot, include an explicit model version and contain no duplicate customers. The current boundary validates files; it does not persist model results, serve models or provide a UI. Future persistence would use separate versioned annotation entities after its requirements are defined.

## Export UML diagrams

```powershell
powershell -File scripts/render-models.ps1 -PlantUmlJar .tools/plantuml.jar
```

The script uses local Java and a PlantUML JAR to write PNGs under `artifacts/models/`. Diagram sources use Smetana layout without a separate Graphviz requirement. Keep both the PNGs and `.puml` sources, and inspect readability before incorporating diagrams into the final PDF.

## Acceptance evidence and remaining coursework

`py -3 scripts/check_delivery.py` audits class coverage, both engine verifications, invalid-write cases, real-data assertions, three-way comparisons, inspected memory limits, UML and the feature contract. `artifacts/database-verification/summary.json` records the six final comparisons; `artifacts/runtime/final-containers.json` records the final inspected container states.

The repository includes three UML PNGs, validation summaries, integrity audits, query plans and comparison evidence. Original CSVs, the full normalized snapshot, per-row query outputs, the real-subset export, customer feature files, credentials and third-party tools remain local and are excluded from Git. Generate them using the steps above. On a fresh clone, inspect the archived acceptance evidence first; prepare the data and regenerate all outputs before rerunning the complete delivery gate.

See [LICENSE](LICENSE) for the code license and [docs/sources.md](docs/sources.md) for the Olist data's separate provenance, version and license records.

1. For demonstrations, use the startup script to run one database at a time. Reloading the same snapshot returns `already_loaded`.
2. Complete three genuine teacher consultations; do not invent dates or approvals.
3. Write the English report, cover and source appendix in the same PDF when requested.
