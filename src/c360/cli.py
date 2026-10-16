import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import contracts, data, database

def compare_results(left, right):
    for field in ("dataset_id", "query_id", "parameters"):
        if left.get(field) != right.get(field):
            raise ValueError(f"Cannot compare different {field}")
    # Ignore ordering but retain duplicate rows (bag semantics).
    canonical = lambda result: sorted(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in result["rows"])
    return dict(equal=canonical(left) == canonical(right), query_id=left["query_id"],
                left_rows=len(left["rows"]), right_rows=len(right["rows"]),
                left_engine=left.get("engine", "unspecified"), right_engine=right.get("engine", "unspecified"))

def main():
    parser = argparse.ArgumentParser(description="Customer 360 database coursework")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="Validate original Olist CSVs and prepare a shared snapshot")
    prepare.add_argument("--raw", default="data/raw")
    prepare.add_argument("--out", default="data/processed")
    load = sub.add_parser("load", help="Initialize and load an immutable snapshot")
    load.add_argument("engine", choices=["mysql", "neo4j"])
    load.add_argument("--dataset", default="data/processed/dataset.json")
    load.add_argument("--batch-size", type=int, default=500)
    query = sub.add_parser("query", help="Execute a business query or constraint audit")
    query.add_argument("engine", choices=["mysql", "neo4j"])
    query.add_argument("query_id", choices=["Q1", "Q2", "Q3", "Q4", "Q5", "constraints"])
    query.add_argument("--params", default="config/query-parameters.json")
    query.add_argument("--out", required=True)
    compare = sub.add_parser("compare")
    compare.add_argument("mysql_result")
    compare.add_argument("neo4j_result")
    compare.add_argument("--out", required=True)
    export = sub.add_parser("export-features", help="Export a retrospective feature contract; no mining")
    export.add_argument("--dataset", default="data/processed/dataset.json")
    export.add_argument("--start", required=True)
    export.add_argument("--end", required=True)
    export.add_argument("--out", required=True)
    validate = sub.add_parser("validate-results", help="Check a separate course's annotations; no database writes")
    validate.add_argument("result")
    validate.add_argument("--features", required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = data.prepare(args.raw, args.out)
        elif args.command == "load":
            result = database.load(args.engine, data.load_dataset(args.dataset), args.batch_size)
        elif args.command == "query":
            params = database.validate_parameters(data.read_json(args.params))
            result = database.query(args.engine, args.query_id, params)
            result.update(engine=args.engine, executed_at=datetime.now(timezone.utc).isoformat())
            data.write_json(args.out, result)
        elif args.command == "compare":
            result = compare_results(data.read_json(args.mysql_result), data.read_json(args.neo4j_result))
            data.write_json(args.out, result)
            if not result["equal"]:
                print(json.dumps(result, indent=2))
                sys.exit(1)
        elif args.command == "export-features":
            features = contracts.export_features(data.load_dataset(args.dataset), args.start, args.end, args.out)
            result = dict(feature_export_id=features["feature_export_id"], customers=len(features["rows"]), output=args.out)
        else:
            result = contracts.validate_results(data.read_json(args.result), data.read_json(args.features))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, OSError, ImportError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")

if __name__ == "__main__":
    main()
