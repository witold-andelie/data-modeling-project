"""Exercise five invalid-write cases inside transactions that always roll back.

MySQL rejects all five natively. Neo4j Community rejects duplicate identity;
its C2-C5 audits detect temporarily invalid values/relationships instead.
No changes are committed, including successful invalid writes in Neo4j.
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from c360 import data, database


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", required=True, choices=["mysql", "neo4j"])
    parser.add_argument("--out", default="artifacts/database-verification")
    args = parser.parse_args()
    checks = []
    empty_input_audit = None
    with database.connection(args.engine) as conn:
        if args.engine == "mysql":
            import mysql.connector
            cases = [
                ("C1", "INSERT INTO customers SELECT * FROM (SELECT customer_id FROM customers LIMIT 1) AS original", 1062),
                ("C2", "UPDATE orders SET record_id='__missing_parent__' ORDER BY order_id LIMIT 1", 1452),
                ("C3", "UPDATE payments SET amount_cents=-1 ORDER BY order_id,payment_sequence LIMIT 1", 3819),
                ("C4", "UPDATE reviews SET score=0 ORDER BY review_record_id LIMIT 1", 3819),
                ("C5", "UPDATE order_items SET item_number=0 ORDER BY order_id,item_number LIMIT 1", 3819),
            ]
            for rule, statement, expected in cases:
                cur = conn.cursor()
                observed = None
                try:
                    cur.execute(statement)
                except mysql.connector.Error as exc:
                    observed = exc.errno
                finally:
                    conn.rollback()
                    cur.close()
                checks.append(dict(rule=rule, enforcement="native", expected_error=expected,
                                   observed_error=observed, passed=observed == expected, rolled_back=True))
        else:
            from neo4j.exceptions import ConstraintError
            tx = conn.begin_transaction()
            rejected = False
            try:
                cid = tx.run("MATCH (c:Customer) RETURN c.customer_id AS id LIMIT 1").single()["id"]
                tx.run("CREATE (:Customer {customer_id:$id})", id=cid).consume()
            except ConstraintError:
                rejected = True
            finally:
                tx.rollback()
            checks.append(dict(rule="C1", enforcement="native", passed=rejected, rolled_back=True))
            audit = "\n".join(line for line in (ROOT / "cypher" / "constraints.cypher").read_text(encoding="utf-8").splitlines()
                              if not line.lstrip().startswith("//")).rstrip().rstrip(";")
            # Exercise the actual audit branches with zero input. Adding a rule
            # literal to an aggregate projection must not hide a clean rule.
            empty_query = " UNION ALL ".join("UNWIND [] AS empty_input " + part.strip()
                                             for part in audit.split("UNION ALL"))
            empty_rows = [dict(r) for r in conn.run(empty_query)]
            expected_rows = data.read_json(ROOT / "artifacts/reference/reference-constraints.json")["rows"]
            canonical = lambda rows: sorted((r["rule"], r["violations"]) for r in rows)
            empty_input_audit = dict(expected_rows=len(expected_rows), actual_rows=len(empty_rows),
                                    passed=canonical(empty_rows) == canonical(expected_rows))
            cases = [
                ("C2", "MATCH (c:CustomerRecord)-[r:IDENTIFIES]->() WITH r LIMIT 1 DELETE r", "C2:customer_records.customer_id"),
                ("C3", "MATCH (p:Payment) WITH p LIMIT 1 SET p.amount_cents=-1", "C3:payments"),
                ("C4", "MATCH (r:Review) WITH r LIMIT 1 SET r.score=0", "C4:reviews"),
                ("C5", "MATCH (i:OrderItem) WITH i LIMIT 1 SET i.item_number=0", "C5:order_items"),
            ]
            for rule, statement, audit_rule in cases:
                clause = next(part.strip() for part in audit.split("UNION ALL") if f"'{audit_rule}'" in part)
                tx = conn.begin_transaction()
                try:
                    tx.run(statement).consume()
                    count = tx.run(clause).single()["violations"]
                finally:
                    tx.rollback()
                checks.append(dict(rule=rule, enforcement="audit", violations=count,
                                   passed=count == 1, rolled_back=True))
    # A fresh connection must see the original zero-violation snapshot.
    params = database.validate_parameters(data.read_json(ROOT / "config/query-parameters.json"))
    clean = database.query(args.engine, "constraints", params)
    summary = dict(engine=args.engine, dataset_id=clean["dataset_id"],
                   executed_at=datetime.now(timezone.utc).isoformat(), checks=checks,
                   clean_after_rollback=all(r["violations"] == 0 for r in clean["rows"]))
    if empty_input_audit is not None:
        summary["empty_input_audit"] = empty_input_audit
    summary["passed"] = (summary["clean_after_rollback"] and all(c["passed"] for c in checks)
                         and (empty_input_audit is None or empty_input_audit["passed"]))
    data.write_json(Path(args.out) / f"{args.engine}-negative-constraints.json", summary)
    print(summary)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
