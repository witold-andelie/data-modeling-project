"""Offline full-data phase. Run with no database loading/querying or UML rendering."""
import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from c360 import data, database, reference


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/processed/dataset.json")
    parser.add_argument("--raw", default="data/raw")
    parser.add_argument("--params", default="config/query-parameters.json")
    parser.add_argument("--out", default="artifacts/reference")
    args = parser.parse_args()
    dataset = data.load_dataset(args.dataset)
    params = database.validate_parameters(data.read_json(args.params))
    if params["customer_id"] not in {r["customer_id"] for r in dataset["tables"]["customers"]}:
        raise ValueError("Query customer must exist in the real snapshot")
    for filename, expected in dataset["source_sha256"].items():
        with (Path(args.raw) / filename).open("rb") as source:
            actual = hashlib.file_digest(source, "sha256").hexdigest()
        if actual != expected:
            raise ValueError(f"Original CSV checksum changed: {filename}")
    output = Path(args.out)
    expectations = reference.evaluate(dataset["tables"], params)
    for query_id, rows in expectations.items():
        data.write_json(output / f"reference-{query_id}.json", dict(dataset_id=dataset["dataset_id"],
                        query_id=query_id, parameters=params, rows=rows, engine="python-reference"))
    small = reference.sample(dataset["tables"], params)
    data.write_json(output / "real-sample.json", dict(dataset_id=dataset["dataset_id"], parameters=params, **small))
    summary = dict(dataset_id=dataset["dataset_id"], generated_at=datetime.now(timezone.utc).isoformat(),
                   source_sha256=dataset["source_sha256"],
                   counts={k: len(v) for k, v in dataset["tables"].items()},
                   expected_rows={k: len(v) for k, v in expectations.items()}, sample_cases=small["cases"],
                   source_checksums_verified=True, passed=True,
                   method="Independent Python sets, integer sums and combinations; no SQL/Cypher",
                   limitation="Algorithmic expectations and reviewable real sample; teacher review remains pending")
    data.write_json(output / "summary.json", summary)
    print(summary)


if __name__ == "__main__":
    main()
