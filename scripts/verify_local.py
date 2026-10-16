"""Persist local checks separately from unexecuted database integration checks."""
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "validation"

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []
    for name, command in [
        ("unit-tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        ("framework", [sys.executable, "scripts/check_framework.py"]),
        ("cli", [sys.executable, "scripts/c360.py", "--help"]),
    ]:
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        (OUT / f"{name}.log").write_text(run.stdout + run.stderr, encoding="utf-8")
        checks.append(dict(check=name, passed=run.returncode == 0, exit_code=run.returncode))
    if shutil.which("docker"):
        run = subprocess.run(["docker", "compose", "--env-file", ".env.example", "config", "--quiet"],
                             cwd=ROOT, capture_output=True, text=True)
        (OUT / "compose.log").write_text(run.stdout + run.stderr, encoding="utf-8")
        checks.append(dict(check="compose-config", passed=run.returncode == 0))
    if importlib.util.find_spec("sqlglot"):
        import sqlglot
        parsed = []
        for path in sorted((ROOT / "sql").rglob("*.sql")):
            sql = re.sub(r"%\((\w+)\)s", lambda match: "2" if match[1] == "low_score" else "'2018-01-01T00:00:00'",
                         path.read_text(encoding="utf-8"))
            nodes = sqlglot.parse(sql, read="mysql")
            parsed.append(dict(file=str(path.relative_to(ROOT)), statements=len(nodes)))
        checks.append(dict(check="optional-sqlglot-parse", passed=True, version=sqlglot.__version__, files=parsed,
                           limitation="Parser check only; not MySQL execution"))
    if importlib.util.find_spec("jsonschema"):
        import jsonschema
        for path in (ROOT / "contracts").glob("*.schema.json"):
            jsonschema.Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
        checks.append(dict(check="optional-json-schema-definitions", passed=True))
    summary = dict(executed_at=datetime.now(timezone.utc).isoformat(), python=sys.version,
                   checks=checks, passed=all(c["passed"] for c in checks),
                   database_execution="not part of this check", uml_rendering="not part of this check")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
