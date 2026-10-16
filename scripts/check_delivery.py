"""Audit saved coursework evidence; never connects to or starts a database."""
import hashlib
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from c360 import data


def main():
    checks = []
    def record(name, callback):
        try:
            ok = bool(callback())
            checks.append(dict(check=name, passed=ok))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            checks.append(dict(check=name, passed=False, detail=str(exc)))
    def read(relative):
        # PowerShell 5.1 evidence files use a UTF-8 BOM.
        import json
        return json.loads((ROOT / relative).read_text(encoding="utf-8-sig"))
    reference = read("artifacts/reference/summary.json")
    params = read("config/query-parameters.json")
    record("local validation", lambda: read("artifacts/validation/summary.json")["passed"])
    record("real data and minimum class coverage", lambda: reference["passed"] and reference["source_checksums_verified"]
           and len(reference["counts"]) == 9 and min(reference["counts"].values()) >= 5)
    def run_valid(engine, suffix):
        result = read(f"artifacts/database-verification/{engine}-{suffix}.json")
        return result["passed"] and result["dataset_id"] == reference["dataset_id"]
    for engine, memory in (("mysql", 536870912), ("neo4j", 1073741824)):
        for suffix in ("summary", "negative-constraints", "real-cases"):
            record(f"{engine} {suffix}", lambda e=engine, s=suffix: run_valid(e, s))
        def memory_valid(e=engine, m=memory):
            result = read(f"artifacts/runtime/{e}.json")
            return (result["memory_bytes"] == m and result["memory_swap_bytes"] == m
                    and not result["oom_killed"] and bool(result["image_digests"]))
        record(f"{engine} inspected limits and image identity", memory_valid)
    def comparison_valid():
        result = read("artifacts/database-verification/summary.json")
        return (result["passed"] and result["dataset_id"] == reference["dataset_id"]
                and result["parameters"] == params and len(result["checks"]) == 6)
    record("three-way query and audit comparison", comparison_valid)
    def shutdown_valid():
        result = read("artifacts/runtime/final-containers.json")
        return (result["all_project_databases_stopped"] and result["volumes_preserved"]
                and len(result["containers"]) == 2
                and all(c["status"] == "exited" and c["exit_code"] == 0 and not c["oom_killed"]
                        for c in result["containers"]))
    record("task databases stopped gracefully with volumes preserved", shutdown_valid)
    def uml_valid():
        manifest = read("artifacts/models/manifest.json")
        if len(manifest["images"]) != 3:
            return False
        for item in manifest["images"]:
            source = ROOT / "models" / item["source"]
            png = ROOT / "artifacts/models" / item["png"]
            if hashlib.sha256(source.read_bytes()).hexdigest() != item["source_sha256"]:
                return False
            with png.open("rb") as stream:
                header = stream.read(24)
            if header[:8] != b"\x89PNG\r\n\x1a\n" or not all(struct.unpack(">II", header[16:24])):
                return False
        return True
    record("three current UML PNGs", uml_valid)
    def features_valid():
        value = read("artifacts/customer-features.json")
        return (value["dataset_id"] == reference["dataset_id"] and value["point_in_time_safe"] is False
                and data.digest({k: v for k, v in value.items() if k != "feature_export_id"}) == value["feature_export_id"]
                and len(value["rows"]) == reference["expected_rows"]["Q2"])
    record("versioned real customer feature export", features_valid)
    record("normalization argument", lambda: (ROOT / "docs/normalization.md").is_file())
    summary = dict(checked_at=datetime.now(timezone.utc).isoformat(), dataset_id=reference["dataset_id"],
                   database_implementation_ready=all(c["passed"] for c in checks), checks=checks,
                   deferred_by_user=["report prose", "cover metadata", "final report PDF and source appendix"],
                   external_requirements=["three genuine teacher consultations; never fabricated"],
                   timing_scope="observed runs only; no controlled performance ranking")
    data.write_json(ROOT / "artifacts/delivery-status.json", summary)
    for check in checks:
        print(f"{'PASS' if check['passed'] else 'PENDING/FAIL'} {check['check']}")
    print("Database implementation ready:", summary["database_implementation_ready"])
    return 0 if summary["database_implementation_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
