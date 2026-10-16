"""Small adapters. Query text remains reviewable in sql/ and cypher/."""
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import os
import re

from .model import ENTITIES, REFERENCES

ROOT = Path(__file__).resolve().parents[2]

def read_environment():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            if line.strip() and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

@contextmanager
def connection(engine):
    read_environment()
    if engine == "mysql":
        import mysql.connector
        conn = mysql.connector.connect(host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3307")), database=os.getenv("MYSQL_DATABASE", "customer360"),
            user=os.getenv("MYSQL_USER", "customer360"), password=os.environ["MYSQL_PASSWORD"],
            connection_timeout=10, use_pure=True)
        try:
            yield conn
        finally:
            conn.close()
    else:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://127.0.0.1:7688"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]))
        try:
            with driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:
                yield session
        finally:
            driver.close()

def statements(path):
    # Project-owned DDL only: no stored procedures or quoted semicolons.
    text = Path(path).read_text(encoding="utf-8")
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(("--", "//")))
    return [part.strip() for part in text.split(";") if part.strip()]

def scalar(value):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else str(value)
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    return value

def validate_parameters(params):
    start, end = datetime.fromisoformat(params["start"]), datetime.fromisoformat(params["end"])
    if start.tzinfo or end.tzinfo or start >= end:
        raise ValueError("Query window requires naive ISO timestamps and start < end")
    # Normalize to the exact sortable representation stored in Neo4j.
    params = dict(params, start=start.isoformat(timespec="seconds"), end=end.isoformat(timespec="seconds"))
    if type(params["low_score"]) is not int or not 1 <= params["low_score"] <= 5:
        raise ValueError("low_score must be an integer from 1 to 5")
    if not isinstance(params["customer_id"], str):
        raise ValueError("customer_id must be a string")
    return params

def query(engine, query_id, params):
    if query_id not in {"Q1", "Q2", "Q3", "Q4", "Q5", "constraints"}:
        raise ValueError("Unknown query ID")
    folder, suffix = ("sql", "sql") if engine == "mysql" else ("cypher", "cypher")
    path = ROOT / folder / (f"queries/{query_id}.{suffix}" if query_id != "constraints" else f"constraints.{suffix}")
    text = path.read_text(encoding="utf-8")
    with connection(engine) as conn:
        if engine == "mysql":
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT dataset_id, status FROM project_snapshot WHERE singleton=1")
            state = cur.fetchone()
            if not state or state["status"] != "complete":
                raise ValueError("Database snapshot has not completed loading")
            # Pass only placeholders actually used by this query.
            used = set(re.findall(r"%\((\w+)\)s", text))
            cur.execute(text, {k: params[k] for k in used})
            rows = [{k: scalar(v) for k, v in row.items()} for row in cur.fetchall()]
            cur.close()
        else:
            record = conn.run("MATCH (s:ProjectSnapshot {id:1}) RETURN s.dataset_id AS dataset_id, s.status AS status").single()
            state = dict(record) if record else None
            if not state or state["status"] != "complete":
                raise ValueError("Database snapshot has not completed loading")
            rows = [dict(r) for r in conn.run(text, params)]
    return dict(dataset_id=state["dataset_id"], query_id=query_id, parameters=params, rows=rows)

def chunks(rows, size=1000):
    for start in range(0, len(rows), size):
        yield rows[start:start + size]

def load(engine, dataset, batch_size=500):
    if type(batch_size) is not int or not 1 <= batch_size <= 1000:
        raise ValueError("batch_size must be an integer from 1 to 1000")
    tables, dataset_id = dataset["tables"], dataset["dataset_id"]
    folder, suffix = ("sql", "sql") if engine == "mysql" else ("cypher", "cypher")
    with connection(engine) as conn:
        if engine == "mysql":
            cur = conn.cursor()
            for stmt in statements(ROOT / folder / f"00_schema.{suffix}"):
                cur.execute(stmt)
            conn.commit()
            try:
                cur.execute("SELECT dataset_id, status FROM project_snapshot WHERE singleton=1 FOR UPDATE")
                state = cur.fetchone()
                if state:
                    if state[0] != dataset_id:
                        raise ValueError("Different snapshot already exists. Use a separate database for a new snapshot.")
                    if state[1] == "complete":
                        return dict(status="already_loaded", dataset_id=dataset_id)
                # MySQL load is atomic: an incomplete prior load rolls back all rows.
                for table in ENTITIES:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    if cur.fetchone()[0]:
                        raise ValueError(f"Unexpected existing rows in {table}; refusing to overwrite")
                cur.execute("INSERT INTO project_snapshot(singleton,dataset_id,status) VALUES(1,%s,'loading')", (dataset_id,))
                for table, rows in tables.items():
                    if not rows:
                        continue
                    columns = list(rows[0])
                    stmt = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join(['%s'] * len(columns))})"
                    for batch in chunks(rows, batch_size):
                        cur.executemany(stmt, [tuple(datetime.fromisoformat(r[c]) if c.endswith('_at') and r[c] else r[c]
                                                     for c in columns) for r in batch])
                cur.execute("UPDATE project_snapshot SET status='complete' WHERE singleton=1")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()
        else:
            for stmt in statements(ROOT / folder / f"00_schema.{suffix}"):
                conn.run(stmt).consume()
            record = conn.run("MATCH (s:ProjectSnapshot {id:1}) RETURN s.dataset_id AS dataset_id, s.status AS status").single()
            if record:
                if record["dataset_id"] != dataset_id:
                    raise ValueError("Different graph snapshot exists. Use a separate database for a new snapshot.")
                if record["status"] == "complete":
                    return dict(status="already_loaded", dataset_id=dataset_id)
            else:
                for label, _ in ENTITIES.values():
                    if conn.run(f"MATCH (n:{label}) RETURN count(n) AS n").single()["n"]:
                        raise ValueError(f"Unexpected existing {label} nodes; refusing to overwrite")
                conn.run("CREATE (:ProjectSnapshot {id:1, dataset_id:$id, status:'loading'})", id=dataset_id).consume()
            # Interrupted loads of the same immutable snapshot resume via MERGE.
            # Only one loader process may run at a time.
            for table, (label, keys) in ENTITIES.items():
                key_map = ", ".join(f"{key}:row.{key}" for key in keys)
                stmt = f"UNWIND $rows AS row MERGE (n:{label} {{{key_map}}}) SET n += row"
                for batch in chunks(tables[table], batch_size):
                    conn.run(stmt, rows=batch).consume()
            for child, fk, parent, pk, relationship in REFERENCES:
                child_label, child_keys = ENTITIES[child]
                parent_label, _ = ENTITIES[parent]
                key_map = ", ".join(f"{key}:row.{key}" for key in child_keys)
                # Bound relationship transactions as well as node transactions.
                # Both endpoints use their native unique indexes, including
                # the composite keys on OrderItem and Payment.
                stmt = (f"UNWIND $rows AS row MATCH (c:{child_label} {{{key_map}}}) "
                        f"MATCH (p:{parent_label} {{{pk}:row.{fk}}}) "
                        f"MERGE (c)-[:{relationship}]->(p)")
                for batch in chunks(tables[child], batch_size):
                    refs = [{key: row[key] for key in set(child_keys) | {fk}}
                            for row in batch if row[fk] is not None]
                    if refs:
                        conn.run(stmt, rows=refs).consume()
            conn.run("MATCH (s:ProjectSnapshot {id:1}) SET s.status='complete'").consume()
    return dict(status="loaded", dataset_id=dataset_id, counts={k: len(v) for k, v in tables.items()})
