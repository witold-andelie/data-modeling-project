# Relational normalization argument

This describes the implemented database model, not report prose. The functional
dependencies below are business assumptions about the stored snapshot. Real
observations can disprove a dependency but cannot prove it for all future data.
Reproduction: `py -3 scripts/profile_source.py`. Evidence:
`artifacts/reference/source-profile.json` and `sql/00_schema.sql`.

## Keys and functional dependencies

Let `K -> rest` mean that the stated candidate key determines every other
attribute in that relation. No further nontrivial dependencies are assumed.

| Relation | Candidate key K | Attributes determined by K |
|---|---|---|
| customers | customer_id | None; this is an identity relation |
| customer_records | record_id | customer_id, zip_prefix, city, state |
| categories | category_name | None; source-backed category vocabulary |
| products | product_id | category_name, weight_g |
| sellers | seller_id | zip_prefix, city, state |
| orders | order_id | record_id, status, purchased_at, approved_at, delivered_at, estimated_at |
| order_items | (order_id, item_number) | product_id, seller_id, price_cents, freight_cents |
| payments | (order_id, payment_sequence) | payment_type, installments, amount_cents |
| reviews | review_record_id | source_review_id, order_id, score, created_at |

An item's product and price are facts about that numbered line. They are not
determined by order_id alone or item_number alone. Payment attributes likewise
depend on the complete order/sequence key. A product does not determine the
price paid across orders. A source review ID is not a candidate key: 100,000
rows have 99,173 distinct IDs, and 802 IDs repeat. Review row surrogates identify
rows within this immutable snapshot only.

## Why the decompositions are necessary

Customer location stays on CustomerRecord. There are 2,997 customers with more
than one source record and 252 with more than one observed location. For
example, customer `004b45ec5c64187465168251cd1c9c2f` has zip prefixes `57035`
and `57055`, both in Maceio/AL. Thus customer_id does not determine one address.

Postal prefix is not used as a location key: 39 observed prefixes map to more
than one city/state spelling. Prefix `06806` appears with both `embu/SP` and
`embu das artes/SP`. Inventing `zip_prefix -> city,state` would introduce an
unsupported dependency. No external municipality normalization is performed.

The observed maximum is one order per source CustomerRecord. The conceptual
model nevertheless allows multiple orders per record: the snapshot does not
establish a permanent business rule making record_id an alternate Order key.

Item, payment and review collections have separate relations. If an order had
two items, two payments and two reviews, flattening them into one relation
would create eight combinations and duplicate monetary values. Q1/Q2 aggregate
payments at order grain before customer aggregation; Q3 counts reviewed orders
once. Product category/weight and seller location remain on their parent
relations, avoiding repetition on every item. Category rows retain actual source
values; 610 products have missing categories and keep a nullable reference.

## Normal forms and limits of the argument

All stored attributes are scalar values at the declared row grain (1NF).
The two composite-key relations have no assumed dependency on a proper subset
of the key; all other keys have one attribute (2NF). No non-key determinant or
transitive non-key dependency is assumed inside a relation (3NF). Under exactly
the dependency set above, every nontrivial determinant is a superkey, so the
nine relations satisfy BCNF. Foreign keys express inter-relation inclusion,
not an extra dependency requiring denormalization of parent attributes.

The identity-only Customer and Category relations admit no nontrivial further
decomposition. No independent multivalued dependency is asserted within the
remaining row grains. Independent order children already occupy separate
relations. No additional semantic join dependency has been established that
would justify decomposing a numbered OrderItem into pairwise order/product/
seller projections; reconstruction could invent combinations and lose item
identity and price. Accordingly the project makes a BCNF argument and records
the 4NF/5NF review, without claiming that data sampling proves every relation
is in 5NF. Missing optional SQL values are retained rather than fabricated;
the dependency argument concerns the meaning of each record.

## Graph mapping

The graph preserves the same nine grains and keys. OrderItem and Payment are
nodes with composite unique constraints. Relationships point from each child
to its referenced parent. Reference ID properties are intentionally retained
for C2 audits. This storage redundancy supports diagnosis and is not described
as relational normalization. Community uniqueness is native; relationship
cardinality, required values and ranges also rely on loading checks and audits.
