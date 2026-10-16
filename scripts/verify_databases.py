"""Verify one loaded engine, or compare saved files with both engines off.

Never starts/stops containers or loads data. Build reference artifacts first.
"""
import argparse
import re
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from c360 import data, database, reference
from c360.cli import compare_results
from c360.model import ENTITIES


def inspect_engine(engine, params, output):
    counts, plans = {}, {}
    with database.connection(engine) as conn:
        if engine == "mysql":
            cur = conn.cursor()
            cur.execute("SELECT VERSION()")
            server_version = cur.fetchone()[0]
            for table in ENTITIES:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cur.fetchone()[0]
            for query_id in reference.QUERY_IDS[:-1]:
                sql = (ROOT / "sql" / "queries" / f"{query_id}.sql").read_text(encoding="utf-8")
                used = set(re.findall(r"%\((\w+)\)s", sql))
                cur.execute("EXPLAIN FORMAT=JSON " + sql, {k: params[k] for k in used})
                plans[query_id] = cur.fetchone()[0]
            cur.close()
        else:
            server_version = conn.run("CALL dbms.components() YIELD versions RETURN versions[0] AS version").single()["version"]
            for table, (label, _) in ENTITIES.items():
                counts[table] = conn.run(f"MATCH (n:{label}) RETURN count(n) AS n").single()["n"]
            for query_id in reference.QUERY_IDS[:-1]:
                cypher = (ROOT / "cypher" / "queries" / f"{query_id}.cypher").read_text(encoding="utf-8")
                plans[query_id] = str(conn.run("EXPLAIN " + cypher, params).consume().plan)
    data.write_json(output / f"{engine}-plans.json", plans)
    return dict(server_version=server_version, counts=counts,
                driver_version=version("mysql-connector-python" if engine == "mysql" else "neo4j"))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--engine", choices=["mysql", "neo4j"])
    mode.add_argument("--compare-only", action="store_true")
    parser.add_argument("--params", default="config/query-parameters.json")
    parser.add_argument("--out", default="artifacts/database-verification")
    parser.add_argument("--reference", default="artifacts/reference")
    args = parser.parse_args()
    output, expected_dir = Path(args.out), Path(args.reference)
    expected_summary = data.read_json(expected_dir / "summary.json")
    if not expected_summary.get("passed") or not expected_summary.get("source_checksums_verified"):
        raise ValueError("Build a verified real-data reference first")
    params = database.validate_parameters(data.read_json(args.params))
    summary = dict(dataset_id=expected_summary["dataset_id"], parameters=params, passed=False,
                   executed_at=datetime.now(timezone.utc).isoformat(), checks=[])
    filename = f"{args.engine}-summary.json" if args.engine else "summary.json"
    try:
        if args.engine:
            for query_id in reference.QUERY_IDS:
                start = perf_counter()
                result = database.query(args.engine, query_id, params)
                result.update(engine=args.engine, executed_at=datetime.now(timezone.utc).isoformat(),
                              elapsed_seconds=round(perf_counter() - start, 6))
                data.write_json(output / f"{args.engine}-{query_id}.json", result)
                check = compare_results(data.read_json(expected_dir / f"reference-{query_id}.json"), result)
                check["elapsed_seconds"] = result["elapsed_seconds"]
                summary["checks"].append(check)
                print(f"{args.engine} {query_id}: {len(result['rows'])} rows, reference_equal={check['equal']}", flush=True)
            details = inspect_engine(args.engine, params, output)
            summary.update(**details, counts_equal=details["counts"] == expected_summary["counts"])
            summary["passed"] = summary["counts_equal"] and all(c["equal"] for c in summary["checks"])
            summary["timing_scope"] = "One observed execution per query including connection; not a controlled benchmark"
        else:
            for engine in ("mysql", "neo4j"):
                run = data.read_json(output / f"{engine}-summary.json")
                if not run["passed"] or run["dataset_id"] != summary["dataset_id"] or run["parameters"] != params:
                    raise ValueError(f"{engine} verification is missing, failed or has different provenance")
                for suffix in ("negative-constraints", "real-cases"):
                    evidence = data.read_json(output / f"{engine}-{suffix}.json")
                    if not evidence["passed"] or evidence["dataset_id"] != summary["dataset_id"]:
                        raise ValueError(f"{engine} {suffix} verification is missing or failed")
            for query_id in reference.QUERY_IDS:
                left = data.read_json(output / f"mysql-{query_id}.json")
                right = data.read_json(output / f"neo4j-{query_id}.json")
                expected = data.read_json(expected_dir / f"reference-{query_id}.json")
                check = compare_results(left, right)
                check["reference_equal"] = compare_results(expected, left)["equal"] and compare_results(expected, right)["equal"]
                if query_id == "constraints":
                    check["zero_violations"] = all(r["violations"] == 0 for result in (left, right) for r in result["rows"])
                summary["checks"].append(check)
                data.write_json(output / f"compare-{query_id}.json", check)
            summary["passed"] = all(c["equal"] and c["reference_equal"] and c.get("zero_violations", True)
                                    for c in summary["checks"])
        summary["limitation"] = "Independent algorithmic reference plus real sample for human inspection; no causal or benchmark claims"
    except Exception as exc:
        summary["error"] = f"{type(exc).__name__}: {exc}"
        print(summary["error"], file=sys.stderr)
    data.write_json(output / filename, summary)
    print(f"{'PASSED' if summary['passed'] else 'FAILED'}: {output / filename}")
    return 0 if summary["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
