# Domain and implementation design

## Business scope

An e-commerce analytics team needs a consistent view of customers, orders,
payments and service experience. It must identify a customer's orders across
source customer records, compute transaction totals without join duplication,
and trace relationships between low-rated orders, sellers and other customers.
The project analyzes historical records; it does not operate a live checkout,
resolve payments, infer personal identities or establish causal responsibility.

## Entity grain

| Entity | One row/node represents | Key |
|---|---|---|
| Customer | One source `customer_unique_id` | customer_id |
| CustomerRecord | One source `customer_id`, with that record's location | record_id |
| Category | One distinct nonmissing source category name | category_name |
| Product | One source product | product_id |
| Seller | One source seller | seller_id |
| Order | One order | order_id |
| OrderItem | One numbered item in an order | (order_id, item_number) |
| Payment | One numbered payment record in an order | (order_id, payment_sequence) |
| Review | One source CSV review row | review_record_id |

The extra CustomerRecord class preserves source identity and order-associated
location. A customer's city is not assumed constant across all orders. The
model permits multiple orders referencing a record; source profiling will
document the observed multiplicity. Customer identity means the provided
pseudonymous ID, not an independently verified person.

Review IDs are retained as attributes, not assumed unique. The surrogate
review key is the CSV record position (header counted as position 1), scoped
to the immutable source snapshot. Every review row is preserved. Consumers
must not treat this surrogate as a stable ID across replacement snapshots.

Categories are derived by projecting distinct source product category values.
This creates no invented category labels. A missing category stays null, so a
product may have zero or one category. Derived category rows count as real
source-backed values, with provenance in products.csv; confirm presentation
with the teacher during consultation.

## Common semantics

- Money is BRL integer cents in both engines; no binary floating point.
- Purchased-at filters are `[start, end)`. Source timestamps have no timezone;
  none is guessed. MySQL stores DATETIME; Neo4j stores normalized ISO local
  strings for matching range/sort semantics at second precision.
- Payment totals describe recorded payment amounts, not net revenue, profit
  or lifetime value. Refund and chargeback completeness is not established.
- All source order statuses participate unless a query explicitly says otherwise.
- Low-rated means at least one review score at or below a chosen threshold.
  Multiple reviews do not duplicate orders in Q3.
- Late means actual delivery timestamp exceeds estimated delivery timestamp.
  Missing dates are excluded from Q3, not imputed as on-time deliveries.
- An association between a seller and a low-rated order does not assign blame:
  an order can contain items from multiple sellers.

## Storage and pipeline

`CSV -> strict parsing -> keys/references/ranges -> canonical dataset + hashes
-> MySQL and Neo4j -> paired query outputs -> comparison evidence`.

The source and prepared snapshots are local ignored artifacts. Preparation is
deterministic. Failed rows remain in the source and are reported; there is no
automatic cleaning. The framework uses one in-memory canonical snapshot,
appropriate as a starting implementation for this dataset, not a claim of
streaming scalability.

Each target database has a technical ProjectSnapshot record, excluded from the
nine business classes. Different dataset hashes cannot be loaded over one
another. MySQL inserts are transactional; Neo4j uses resumable batches and a
completion marker. Queries reject incomplete snapshots. Concurrent loading is
outside the supported workflow. Schemas are version 1.0; IF NOT EXISTS is not
a schema migration mechanism.

Neo4j retains the reference ID properties as well as relationships. This is
deliberate audit redundancy: C2 checks that each edge agrees with its source
reference. Community uniqueness constraints do not enforce every required
property, range or relationship multiplicity; preparation checks and explicit
audits complement native constraints. The loader uses internal parameterized
queries. It does not use triggers, stored procedures or APOC.

## Normalization

`docs/normalization.md` enumerates candidate keys and semantic dependencies,
gives a BCNF argument under those dependencies and records the limits of the
4NF/5NF review. The independent raw-CSV profile finds 252 customers with more
than one observed location and 39 postal prefixes with multiple city/state
spellings. Those observations refute location shortcuts; they do not prove
new semantic dependencies. Orders, items, payments and reviews retain distinct
grains. DDL checks alone are not a normalization proof.

## Extension boundary

The separate data-mining course consumes `contracts/features.schema.json` and
returns `contracts/results.schema.json`. It can select algorithms independently.
This project implements feature aggregation and return-file validation only.
No model state or derived label is stored on Customer. A later persistence
adapter must use separate versioned annotation entities and retain the source
feature hash. Its design must not add invented business instances to the course
data or change Q1–Q5 semantics.
