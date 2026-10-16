# Source register

Web sources inspected on 2026-10-16. These links establish design context; they
are not evidence that a dataset download or database execution has occurred.

| Source | URL | Use |
|---|---|---|
| Olist original dataset | https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce | CSV download, source data and license verification |
| Olist dataset metadata | https://www.kaggle.com/olistbr/brazilian-ecommerce/metadata | customer_id vs customer_unique_id semantics |
| Olist employee's release announcement | https://www.kaggle.com/general/67613 | Real anonymized commercial data provenance |
| SAP target vacancy | https://jobs.sap.com/en/jobs/744000153159823/sap-ixp-intern-it-data-analytics-limited-part-time/ | Customer 360, SQL, data pipelines and quality alignment |
| MySQL 8.4 CHECK documentation | https://dev.mysql.com/doc/refman/8.4/en/create-table-check-constraints.html | Native row constraint design |
| Neo4j constraint documentation | https://neo4j.com/docs/cypher-manual/current/constraints/managing-constraints/ | Native uniqueness versus additional audits |
| PlantUML class diagrams | https://plantuml.com/class-diagram | Class diagram syntax |

Local reference inventory (title pages and database book contents inspected):

- `../bok 978-3-658-24549-8.pdf`: Andreas Meier and Michael Kaufmann,
  *SQL & NoSQL Databases*. Relevant contents: dependencies/normal forms,
  relational and graph mappings, integrity constraints, SQL and Cypher.
- `../book 978-3-658-06823-3.pdf`: Johannes Brauer,
  *Programming Smalltalk – Object-Orientation from the Beginning*.

The five originally named reference PDFs were not present at the supplied
directory during inspection. No claim of reading those files is made.

When data is acquired, record dataset version, retrieval date, original license
and redistribution terms, source URL and original archive checksum. The prepare
command records individual CSV SHA-256 hashes. Do not commit the source data by
default. Final bibliography entries will be verified when writing the report.

## Acquisition on 2026-10-16

No Kaggle API credential was available, so the seven required CSVs were not
taken from a Kaggle zip and no official archive checksum was obtained. They
were downloaded from the public Git mirror
`spdrio/Brazilian-E-Commerce-Public-Dataset-by-Olist`, commit
`fa0cc6d1aff713d3c8b9a1e633b56889881848bf` (tree dated 2020-09-03). That
repository's README attributes the files to
<https://www.kaggle.com/olistbr/brazilian-ecommerce> and repeats Olist's
statement that the commercial data is anonymized. The Kaggle dataset page
states the license as CC BY-NC-SA 4.0. Coursework use is non-commercial.
The CSVs stay in ignored `data/raw/` and are not committed.

Each downloaded file matched the Git blob size. `py -3 scripts/c360.py prepare`
then hashed the bytes and accepted the snapshot with zero issues. Counts:
customers 96,096; customer records 99,441; categories 73; products 32,951;
sellers 3,095; orders 99,441; order items 112,650; payments 103,886; reviews
100,000. Purchase timestamps run from 2016-09-04 21:15:19 through
2018-10-17 17:30:18, with no timezone in the source. Six hundred ten products
have an empty category and remain uncategorized. Review `review_id` is not
unique: 100,000 rows contain 99,173 distinct source review IDs, 802 IDs repeat,
and the highest multiplicity is 3. The model keeps every row under a
snapshot-scoped surrogate, as specified. No cleaning policy was required.

Column widths fit the MySQL DDL: zip prefixes are at most 5 characters, state
codes are 2, the longest category name is 46, and the longest city is 40.
File SHA-256 values are in `data/processed/quality.json`.

## Reproducible implementation evidence — 2026-10-16

`scripts/build_reference.py` rechecked the original seven CSV hashes against
the immutable prepared snapshot before generating independent Python query
expectations. `scripts/profile_source.py` scans original CSVs separately and
archives observed multiplicities and counterexamples under `artifacts/reference/`.
The generic CC BY-NC-SA 4.0 license text was retrieved from
<https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.txt> and retained
locally as `data/raw/LICENSE-CC-BY-NC-SA-4.0.txt`. This is a copy of the license
text, not evidence of an official Kaggle archive checksum; that limitation remains.

PlantUML 1.2026.8 was downloaded from Maven Central's
`net/sourceforge/plantuml/plantuml/1.2026.8/` publication. The published SHA-1
was checked before executing the JAR, and its SHA-256 is recorded in
`artifacts/models/manifest.json`. Source bytes and rendered PNGs are retained
with a rendering timestamp. The Java heap is capped at 256MiB.
