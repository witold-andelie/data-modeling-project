# Query and constraint specification (draft v1)

The notation below is a typed lambda calculus extended with finite sets,
arithmetic and first-order logic. Aggregates are defined explicitly. This is a
working formal specification for teacher review, not a substitute for executing
the SQL/Cypher. All five business queries have implementations under their IDs.

## Domains and notation

Let C, R, K, P, S, O, I, A and V be finite sets of Customer, CustomerRecord,
Category, Product, Seller, Order, OrderItem, Payment and Review records.
Every record has the attributes in `docs/design.md` and the model sources.
`⊥` denotes a missing value. `∃!` means exactly one. Equality on records includes
record identity. Set comprehensions return distinct tuples; SQL/Cypher use
DISTINCT where required to implement that semantics.

For finite set X, `|X|` is its cardinality. `sum(f,X)` sums `f(x)` over `x ∈ X`,
with `sum(f,∅)=0`. `1[φ]` is 1 when φ holds, otherwise 0. Category-name `<` is
lexicographic ordering; category names are retained from the source. All times
are source-local second-precision timestamps; `a < b` is required.

Define:

```text
W = λa. λb. {o ∈ O | a ≤ o.purchased_at < b}
owner = λo. the unique c ∈ C such that
             ∃r ∈ R: o.record_id = r.record_id ∧ r.customer_id = c.customer_id
paid = λo. sum(λp. p.amount_cents, {p ∈ A | p.order_id = o.order_id})
reviews = λo. {v ∈ V | v.order_id = o.order_id}
low = λτ. λo. ∃v ∈ reviews(o): v.score ≤ τ
sellers = λo. {s ∈ S | ∃i ∈ I: i.order_id = o.order_id ∧ i.seller_id = s.seller_id}
categories = λo. {k ∈ K | ∃i ∈ I, p ∈ P:
                   i.order_id = o.order_id ∧ i.product_id = p.product_id
                   ∧ p.category_name = k.category_name}
```

## Q1 — Customer order overview

Return the selected customer's orders purchased within the observation window,
including order ID, status, purchase timestamp and total recorded payment cents.
Include orders with no payment records and report their payment total as zero.

```text
Q1 = λcustomerId. λa. λb.
     {(o.order_id, o.status, o.purchased_at, paid(o)) |
       o ∈ W(a)(b) ∧ owner(o).customer_id = customerId}
```

Implementation: `sql/queries/Q1.sql`, `cypher/queries/Q1.cypher`.

## Q2 — Customer transaction totals

For each customer with at least one order in the observation window, return
the customer ID, number of orders and total recorded payment cents. Include
all order statuses. Payment totals are not interpreted as revenue or profit.

```text
ordersOf = λc. λa. λb. {o ∈ W(a)(b) | owner(o) = c}
Q2 = λa. λb.
     {(c.customer_id, |ordersOf(c)(a)(b)|, sum(paid, ordersOf(c)(a)(b))) |
       c ∈ C ∧ |ordersOf(c)(a)(b)| > 0}
```

Implementation: `sql/queries/Q2.sql`, `cypher/queries/Q2.cypher`.

## Q3 — Delivery groups and low ratings

For reviewed orders purchased in the window with known actual and estimated
delivery timestamps, return each observed delivery group, its order count and
the count of orders with at least one rating at or below threshold τ. Each
order contributes once, even when it has multiple reviews. A late delivery
means its actual timestamp is strictly greater than its estimate.

```text
eligible = λa. λb. {o ∈ W(a)(b) |
             o.delivered_at ≠ ⊥ ∧ o.estimated_at ≠ ⊥ ∧ |reviews(o)| > 0}
group = λo. if o.delivered_at > o.estimated_at then "late" else "on_time"
Q3 = λτ. λa. λb.
     {(g, |E_g|, sum(λo. 1[low(τ)(o)], E_g)) |
       g ∈ {group(o) | o ∈ eligible(a)(b)},
       E_g = {o ∈ eligible(a)(b) | group(o) = g}}
```

The low-rating proportion is derived from the two counts, not asserted as a
causal effect. No empty group with an artificial zero count is added.

## Q4 — Customers linked to sellers on low-rated orders

Find sellers participating in at least one low-rated order during the window.
Return distinct seller/customer pairs for customers who purchased from any
of those sellers during the same window. The returned customers need not have
submitted a low rating. The query identifies associations, not seller blame.

```text
flagged = λτ. λa. λb.
          {s ∈ S | ∃o ∈ W(a)(b): low(τ)(o) ∧ s ∈ sellers(o)}
Q4 = λτ. λa. λb.
     {(s.seller_id, c.customer_id) | s ∈ flagged(τ)(a)(b) ∧ c ∈ C
       ∧ ∃o ∈ W(a)(b): owner(o) = c ∧ s ∈ sellers(o)}
```

## Q5 — Category co-occurrence counts

Return each unordered pair of distinct known categories appearing together in
at least one order in the observation window, with its number of shared orders.
Count an order only once per pair regardless of its item multiplicity.
This is a descriptive database query, not an association-rule mining module.

```text
shared = λx. λy. λa. λb.
         {o ∈ W(a)(b) | x ∈ categories(o) ∧ y ∈ categories(o)}
Q5 = λa. λb.
     {(x.category_name, y.category_name, |shared(x)(y)(a)(b)|) |
       x ∈ K ∧ y ∈ K ∧ x.category_name < y.category_name
       ∧ |shared(x)(y)(a)(b)| > 0}
```

## C1 — Entity identity

Every entity has a present, unique key in its own class. OrderItem and Payment
use composite keys; Review uses its source-row surrogate, not source_review_id.

```text
validKey = λT. λkey.
  (∀x ∈ T: every component of key(x) is neither ⊥ nor empty)
  ∧ (∀x,y ∈ T: key(x)=key(y) ⇒ x=y)
C1 = ∧_{T in {C,R,K,P,S,O,I,A,V}} validKey(T)(key_T)
```

## C2 — Referential integrity and graph relationship agreement

Every required reference resolves to exactly one parent. A product's category
may be missing; otherwise it resolves to exactly one Category. In the graph,
the matching relationship must point to that same parent and have the expected
cardinality (zero for a missing category, one otherwise).

```text
ref = λX. λY. λfk. λpk. ∀x ∈ X: ∃!y ∈ Y: fk(x)=pk(y)
C2 = ref(R)(C)(customer_id)(customer_id)
   ∧ ref(O)(R)(record_id)(record_id)
   ∧ ref(I)(O)(order_id)(order_id)
   ∧ ref(I)(P)(product_id)(product_id)
   ∧ ref(I)(S)(seller_id)(seller_id)
   ∧ ref(A)(O)(order_id)(order_id)
   ∧ ref(V)(O)(order_id)(order_id)
   ∧ ∀p ∈ P: p.category_name=⊥ ∨
                  ∃!k ∈ K: p.category_name=k.category_name
```

Here a bare attribute name denotes its projection lambda, e.g.
`customer_id = λx. x.customer_id`. For each reference with graph relationship
type L, require `{y | x -L-> y} = {y ∈ Y | fk(x)=pk(y)}`. When the optional
reference is missing, require that outgoing L-edge set to be empty.

## C3 — Nonnegative monetary amounts

Item price, item freight and payment amount must be present nonnegative
integer cents. No equality between summed payments and merchandise value is
assumed without investigating actual source conventions.

```text
money = λn. n ∈ ℤ ∧ n ≥ 0
C3 = (∀i ∈ I: money(i.price_cents) ∧ money(i.freight_cents))
   ∧ (∀p ∈ A: money(p.amount_cents))
```

## C4 — Valid review scores

Every retained review record has an integer score from one through five.

```text
validScore = λv. v.score ∈ ℤ ∧ 1 ≤ v.score ≤ 5
C4 = ∀v ∈ V: validScore(v)
```

## C5 — Positive sequence numbers

Order-item numbers and payment sequence numbers are positive integers within
their parent orders. Uniqueness within an order is already covered by C1.

```text
positive = λn. n ∈ ℤ ∧ n > 0
C5 = (∀i ∈ I: positive(i.item_number))
   ∧ (∀p ∈ A: positive(p.payment_sequence))
```

Enforcement: MySQL primary/foreign keys, NOT NULL and CHECK clauses;
Neo4j native uniqueness plus validated loading and explicit audit queries.
Graph range/cardinality checks are not claimed to prevent arbitrary direct
writes. Audit files: `sql/constraints.sql`, `cypher/constraints.cypher`.
