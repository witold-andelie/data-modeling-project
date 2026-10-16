"""Low-memory CSV profiling, independent of prepared JSON and the databases."""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from c360 import data


def rows(name):
    with (ROOT / "data/raw" / data.FILES[name]).open(encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def main():
    customer_counts, record_orders, review_ids = Counter(), Counter(), Counter()
    locations, zip_locations = defaultdict(set), defaultdict(set)
    for row in rows("customer_records"):
        cid = row["customer_unique_id"]
        customer_counts[cid] += 1
        location = (row["customer_city"], row["customer_state"])
        locations[cid].add((row["customer_zip_code_prefix"], *location))
        zip_locations[row["customer_zip_code_prefix"]].add(location)
    statuses = Counter()
    first = last = None
    for row in rows("orders"):
        record_orders[row["customer_id"]] += 1
        statuses[row["order_status"]] += 1
        stamp = row["order_purchase_timestamp"]
        first = stamp if first is None else min(first, stamp)
        last = stamp if last is None else max(last, stamp)
    for row in rows("reviews"):
        review_ids[row["review_id"]] += 1
    products, unknown_category = 0, 0
    for row in rows("products"):
        products += 1
        unknown_category += not row["product_category_name"]
    multi_zip = next((dict(zip_prefix=key, city_states=sorted(values))
                      for key, values in sorted(zip_locations.items()) if len(values) > 1), None)
    multi_location = next((dict(customer_id=key, locations=sorted(values))
                           for key, values in sorted(locations.items()) if len(values) > 1), None)
    result = dict(customer_count=len(customer_counts), customer_record_count=sum(customer_counts.values()),
                  customers_with_multiple_records=sum(n > 1 for n in customer_counts.values()),
                  max_records_per_customer=max(customer_counts.values()),
                  customers_with_multiple_locations=sum(len(v) > 1 for v in locations.values()),
                  customer_location_counterexample=multi_location,
                  zip_prefixes_with_multiple_city_states=sum(len(v) > 1 for v in zip_locations.values()),
                  zip_location_counterexample=multi_zip,
                  observed_max_orders_per_customer_record=max(record_orders.values()),
                  source_review_rows=sum(review_ids.values()), distinct_source_review_ids=len(review_ids),
                  repeated_source_review_ids=sum(n > 1 for n in review_ids.values()),
                  max_source_review_id_multiplicity=max(review_ids.values()),
                  products=products, products_without_category=unknown_category,
                  purchase_timestamp_min=first, purchase_timestamp_max=last, order_statuses=dict(statuses),
                  limitation="Observed dependencies may refute a proposed FD; they do not establish a semantic FD")
    data.write_json(ROOT / "artifacts/reference/source-profile.json", result)
    print(result)


if __name__ == "__main__":
    main()
