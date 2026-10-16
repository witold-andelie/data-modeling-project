"""Fast structural checks; does not pretend to execute database queries."""
from pathlib import Path
import ast
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from c360.model import ENTITIES

def main():
    errors = []
    for path in list((ROOT / "src").rglob("*.py")) + list((ROOT / "scripts").glob("*.py")):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for path in (ROOT / "config").glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    for query_id in range(1, 6):
        for folder, suffix in [("sql", "sql"), ("cypher", "cypher")]:
            path = ROOT / folder / "queries" / f"Q{query_id}.{suffix}"
            if not path.exists() or not path.read_text().strip():
                errors.append(str(path))
    for name in ("conceptual", "relational", "graph"):
        path = ROOT / "models" / f"{name}.puml"
        if not path.exists():
            errors.append(str(path))
        else:
            text = path.read_text()
            if "@startuml" not in text or "@enduml" not in text:
                errors.append(f"Invalid boundaries: {path}")
            for label, _ in ENTITIES.values():
                if label not in text:
                    errors.append(f"Missing {label} in {name}")
    if errors:
        raise SystemExit("\n".join(errors))
    print("Framework structure OK: Python syntax, configuration, five query pairs and three model sources.")

if __name__ == "__main__":
    main()
