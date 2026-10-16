"""Synthetic fixtures are test data only, never coursework evidence of real data."""
import copy
import csv
import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from c360 import contracts, data, reference
from c360.cli import compare_results
from c360.database import validate_parameters

def source_fixture(folder):
    rows = {key: [] for key in data.FILES}
    for n in range(1, 7):
        # Six source identities represent five real-world identities in this TEST fixture.
        identity = min(n, 5)
        rows["customer_records"].append(dict(customer_id=f"record{n}", customer_unique_id=f"customer{identity}",
            customer_zip_code_prefix="01234", customer_city="Test City", customer_state="TS"))
        rows["products"].append(dict(product_id=f"product{n}", product_category_name=f"category{n}", product_weight_g="100"))
        rows["sellers"].append(dict(seller_id=f"seller{n}", seller_zip_code_prefix="01234", seller_city="Test City", seller_state="TS"))
        rows["orders"].append(dict(order_id=f"order{n}", customer_id=f"record{n}", order_status="delivered",
            order_purchase_timestamp=f"2018-01-0{n} 10:00:00", order_approved_at=f"2018-01-0{n} 11:00:00",
            order_delivered_customer_date="2018-01-20 10:00:00", order_estimated_delivery_date="2018-01-19 00:00:00"))
        rows["order_items"].append(dict(order_id=f"order{n}", order_item_id="1", product_id=f"product{n}",
            seller_id=f"seller{n}", price="10.00", freight_value="2.00"))
        rows["payments"].append(dict(order_id=f"order{n}", payment_sequential="1", payment_type="credit_card",
            payment_installments="1", payment_value="12.00"))
        rows["reviews"].append(dict(review_id="shared-source-review-id", order_id=f"order{n}",
            review_score="2", review_creation_date="2018-01-21 00:00:00"))
    # Two items and two payment records on order1 exercise join fan-out.
    rows["order_items"].append(dict(rows["order_items"][0], order_item_id="2", product_id="product2"))
    rows["payments"].append(dict(rows["payments"][0], payment_sequential="2", payment_value="3.25"))
    for table, filename in data.FILES.items():
        with (folder / filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[table][0]))
            writer.writeheader()
            writer.writerows(rows[table])

class CoreTests(unittest.TestCase):
    def setUp(self):
        workspace = Path(__file__).resolve().parents[1]
        self.root = workspace / "artifacts" / "test-work" / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        # Only remove the exact per-test directory verified within this workspace.
        if not self.root.resolve().is_relative_to(workspace.resolve()):
            raise RuntimeError("Test directory escaped workspace")
        self.addCleanup(shutil.rmtree, self.root)
        self.raw, self.out = self.root / "raw", self.root / "out"
        self.raw.mkdir()
        source_fixture(self.raw)
        data.prepare(self.raw, self.out)
        self.dataset = data.load_dataset(self.out / "dataset.json")

    def features(self):
        return contracts.export_features(self.dataset, "2018-01-01T00:00:00", "2018-02-01T00:00:00", self.root / "features.json")

    def result(self, features):
        return dict(schema_version="1.0", model_id="external-test", model_version="1",
                    generated_at="2026-10-16T10:00:00Z", feature_export_id=features["feature_export_id"],
                    assignments=[dict(customer_id="customer1", label="test-label", score=0.5)])

    def test_identity_and_source_review_rows_preserved(self):
        tables = self.dataset["tables"]
        self.assertEqual(len(tables["customers"]), 5)
        self.assertEqual(len(tables["customer_records"]), 6)
        self.assertEqual(len({r["review_record_id"] for r in tables["reviews"]}), 6)
        self.assertEqual(tables["customer_records"][0]["zip_prefix"], "01234")

    def test_exact_money(self):
        self.assertEqual(data.cents("0.29"), 29)
        for value in ("1.001", "NaN", "Infinity", "-1.00"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                data.cents(value)
        self.assertEqual(data.optional_int("225.0"), 225)
        with self.assertRaises(ValueError):
            data.optional_int("225.5")

    def test_missing_purchase_timestamp_blocks_preparation(self):
        path = self.raw / data.FILES["orders"]
        path.write_text(path.read_text().replace("2018-01-01 10:00:00", "", 1))
        with self.assertRaises(ValueError):
            data.prepare(self.raw, self.out)
        with self.assertRaisesRegex(ValueError, "preparation"):
            data.load_dataset(self.out / "dataset.json")

    def test_preparation_is_deterministic(self):
        data.prepare(self.raw, self.out)
        self.assertEqual(data.load_dataset(self.out / "dataset.json")["dataset_id"], self.dataset["dataset_id"])

    def test_source_parse_failure_has_file_and_line(self):
        path = self.raw / data.FILES["payments"]
        path.write_text(path.read_text().replace("12.00", "bad", 1))
        with self.assertRaises(ValueError):
            data.prepare(self.raw, self.out)
        report = data.read_json(self.out / "quality.json")
        self.assertFalse(report["ready"])
        self.assertEqual(report["issues"][0]["line"], 2)
        with self.assertRaisesRegex(ValueError, "preparation"):
            data.load_dataset(self.out / "dataset.json")

    def test_constraint_violations_are_not_silently_fixed(self):
        tables = copy.deepcopy(self.dataset["tables"])
        tables["customers"].append(dict(tables["customers"][0]))
        tables["orders"][0]["record_id"] = "absent"
        tables["payments"][0]["amount_cents"] = -1
        tables["reviews"][0]["score"] = 6
        tables["order_items"][0]["item_number"] = 0
        self.assertEqual({v["rule"] for v in data.violations(tables)}, {"C1", "C2", "C3", "C4", "C5"})

    def test_snapshot_tampering_rejected(self):
        self.dataset["tables"]["customers"][0]["customer_id"] = "changed"
        data.write_json(self.out / "dataset.json", self.dataset)
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            data.load_dataset(self.out / "dataset.json")

    def test_feature_totals_avoid_fanout_and_merge_customer_records(self):
        features = self.features()
        by_id = {r["customer_id"]: r for r in features["rows"]}
        self.assertEqual(by_id["customer1"]["payment_total_cents"], 1525)
        self.assertEqual(by_id["customer5"]["order_count"], 2)
        self.assertFalse(features["point_in_time_safe"])

    def test_exclusive_window_boundary(self):
        features = contracts.export_features(self.dataset, "2018-01-01T10:00:00", "2018-01-02T10:00:00", self.root / "features.json")
        self.assertEqual([r["customer_id"] for r in features["rows"]], ["customer1"])

    def test_external_result_contract(self):
        features = self.features()
        self.assertTrue(contracts.validate_results(self.result(features), features)["valid"])
        for change in (dict(feature_export_id="wrong"), dict(model_version=""),
                       dict(generated_at="2026-10-16T10:00:00"), dict(assignments=[])):
            with self.subTest(change=change), self.assertRaises(ValueError):
                contracts.validate_results(dict(self.result(features), **change), features)

    def test_external_unknown_duplicates_and_nan_rejected(self):
        features = self.features()
        for assignments in ([dict(customer_id="unknown", label="x")],
                            [dict(customer_id="customer1", label="x")] * 2,
                            [dict(customer_id="customer1", label="x", score=float("nan"))]):
            with self.subTest(assignments=assignments), self.assertRaises(ValueError):
                contracts.validate_results(dict(self.result(features), assignments=assignments), features)

    def test_compare_preserves_duplicates_and_requires_same_provenance(self):
        left = dict(dataset_id="a", query_id="Q1", parameters={}, rows=[dict(x=1), dict(x=2)])
        self.assertTrue(compare_results(left, dict(left, rows=list(reversed(left["rows"]))))["equal"])
        self.assertFalse(compare_results(left, dict(left, rows=left["rows"] + [dict(x=1)]))["equal"])
        with self.assertRaises(ValueError):
            compare_results(left, dict(left, dataset_id="b"))

    def test_window_normalization(self):
        params = dict(customer_id="c", low_score=2, start="2018-01-01", end="2019-01-01")
        self.assertEqual(validate_parameters(params)["start"], "2018-01-01T00:00:00")
        with self.assertRaises(ValueError):
            validate_parameters(dict(params, end="2017-01-01"))

    def test_independent_reference_handles_fanout_and_identity(self):
        params = dict(customer_id="customer1", low_score=2, start="2018-01-01T00:00:00", end="2018-02-01T00:00:00")
        result = reference.evaluate(self.dataset["tables"], params)
        self.assertEqual(result["Q1"][0]["payment_total_cents"], 1525)
        self.assertEqual(result["Q2"][-1], dict(customer_id="customer5", order_count=2, payment_total_cents=2400))
        self.assertEqual(result["Q3"], [dict(delivery_group="late", reviewed_orders=6, low_rated_orders=6)])
        self.assertEqual(result["Q5"], [dict(category_a="category1", category_b="category2", shared_orders=1)])
        self.assertEqual(len(result["constraints"]), 22)

    def test_reference_zero_payments_duplicate_reviews_and_window(self):
        tables = copy.deepcopy(self.dataset["tables"])
        tables["payments"] = [r for r in tables["payments"] if r["order_id"] != "order1"]
        tables["reviews"].append(dict(tables["reviews"][0], review_record_id="extra"))
        params = dict(customer_id="customer1", low_score=2, start="2018-01-01T10:00:00", end="2018-01-02T10:00:00")
        result = reference.evaluate(tables, params)
        self.assertEqual(result["Q1"][0]["payment_total_cents"], 0)
        self.assertEqual(result["Q3"][0]["reviewed_orders"], 1)
        self.assertEqual(len(result["Q4"]), 1)
        small = reference.sample(tables, params)
        self.assertFalse(data.violations(small["tables"]))

if __name__ == "__main__":
    unittest.main()
