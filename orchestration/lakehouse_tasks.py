from __future__ import annotations

import csv
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

from neo4j import GraphDatabase
from trino.dbapi import connect


ROOT_DIR = Path(__file__).resolve().parents[1]
EXPORT_ROOT = ROOT_DIR / "runtime" / "exports"
NEO4J_IMPORT_ROOT = ROOT_DIR / "runtime" / "neo4j" / "import"
LOGGER = logging.getLogger(__name__)


def _trino_connection():
    return connect(
        host=os.getenv("TRINO_HOST", "trino"),
        port=int(os.getenv("TRINO_PORT", "8080")),
        user=os.getenv("TRINO_USER", "airflow"),
        catalog=os.getenv("TRINO_CATALOG", "iceberg"),
        schema=os.getenv("TRINO_SCHEMA", "payments"),
    )


def _validate_identifier(value: str, label: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", value):
        raise ValueError(f"{label} invalido: {value}")
    return value


def _normalize_iso8601(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.isoformat().replace("+00:00", "Z")


def compact_table(table_name: str) -> None:
    safe_table = _validate_identifier(table_name, "table_name")
    catalog = os.getenv("TRINO_CATALOG", "iceberg")
    schema = os.getenv("TRINO_SCHEMA", "payments")
    statement = (
        f"ALTER TABLE {catalog}.{schema}.{safe_table} "
        "EXECUTE optimize(file_size_threshold => '64MB')"
    )
    conn = _trino_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(statement)
        cursor.fetchall()
    except Exception as exc:
        # In low-memory local environments Trino can drop the connection during optimize.
        # Compaction is useful but not required for exporting and loading the graph.
        LOGGER.warning("Se omite la compactacion de %s.%s.%s: %s", catalog, schema, safe_table, exc)
    finally:
        conn.close()


def _build_graph_query(start_ts: str | None, end_ts: str | None) -> str:
    catalog = os.getenv("TRINO_CATALOG", "iceberg")
    schema = os.getenv("TRINO_SCHEMA", "payments")
    predicates: list[str] = []
    if start_ts:
        predicates.append(f"event_time >= from_iso8601_timestamp('{start_ts}')")
    if end_ts:
        predicates.append(f"event_time < from_iso8601_timestamp('{end_ts}')")

    where_clause = f"WHERE {' AND '.join(predicates)}" if predicates else ""
    return f"""
    SELECT
        payment_id,
        payment_group_id,
        CAST(event_time AS VARCHAR) AS event_time,
        customer_id,
        card_id,
        merchant_id,
        device_id,
        ip,
        country,
        CAST(amount AS DOUBLE) AS amount,
        currency,
        status,
        mcc,
        CAST(risk_score AS INTEGER) AS risk_score,
        reasons_text,
        is_alert
    FROM {catalog}.{schema}.graph_payments
    {where_clause}
    """


def fetch_graph_rows(start_ts: str | None, end_ts: str | None) -> list[dict[str, object]]:
    query = _build_graph_query(_normalize_iso8601(start_ts), _normalize_iso8601(end_ts))
    conn = _trino_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
    finally:
        conn.close()
    return [dict(zip(columns, row, strict=False)) for row in rows]


def _write_csvs(directory: Path, datasets: dict[str, tuple[list[str], Iterable[dict[str, object]]]]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for filename, (fieldnames, rows) in datasets.items():
        with (directory / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def export_graph_dataset(graph_name: str, start_ts: str | None = None, end_ts: str | None = None) -> dict[str, int]:
    safe_graph = _validate_identifier(graph_name, "graph_name")
    rows = fetch_graph_rows(start_ts, end_ts)

    customers: dict[str, dict[str, object]] = {}
    cards: dict[str, dict[str, object]] = {}
    devices: dict[str, dict[str, object]] = {}
    merchants: dict[str, dict[str, object]] = {}
    payments: dict[str, dict[str, object]] = {}
    rel_customer_card: dict[tuple[str, str], dict[str, object]] = {}
    rel_card_device: dict[tuple[str, str], dict[str, object]] = {}
    rel_card_payment: dict[tuple[str, str], dict[str, object]] = {}
    rel_payment_merchant: dict[tuple[str, str], dict[str, object]] = {}

    for row in rows:
        customer_id = str(row["customer_id"])
        card_id = str(row["card_id"])
        device_id = str(row["device_id"])
        merchant_id = str(row["merchant_id"])
        payment_id = str(row["payment_id"])

        customers[customer_id] = {"customer_id": customer_id}
        cards[card_id] = {"card_id": card_id}
        devices[device_id] = {"device_id": device_id}
        merchants[merchant_id] = {"merchant_id": merchant_id, "country": row["country"], "mcc": row["mcc"]}
        payments[payment_id] = {
            "payment_id": payment_id,
            "payment_group_id": row["payment_group_id"] or "",
            "event_time": row["event_time"],
            "amount": row["amount"],
            "currency": row["currency"],
            "status": row["status"],
            "country": row["country"],
            "risk_score": row["risk_score"],
            "reasons": row["reasons_text"] or "",
            "is_alert": bool(row["is_alert"]),
            "ip": row["ip"],
            "graph_name": safe_graph,
        }

        rel_customer_card[(customer_id, card_id)] = {"customer_id": customer_id, "card_id": card_id}
        rel_card_device[(card_id, device_id)] = {"card_id": card_id, "device_id": device_id}
        rel_card_payment[(card_id, payment_id)] = {"card_id": card_id, "payment_id": payment_id}
        rel_payment_merchant[(payment_id, merchant_id)] = {"payment_id": payment_id, "merchant_id": merchant_id}

    datasets = {
        "customers.csv": (["customer_id"], customers.values()),
        "cards.csv": (["card_id"], cards.values()),
        "devices.csv": (["device_id"], devices.values()),
        "merchants.csv": (["merchant_id", "country", "mcc"], merchants.values()),
        "payments.csv": (
            [
                "payment_id",
                "payment_group_id",
                "event_time",
                "amount",
                "currency",
                "status",
                "country",
                "risk_score",
                "reasons",
                "is_alert",
                "ip",
                "graph_name",
            ],
            payments.values(),
        ),
        "rel_customer_card.csv": (["customer_id", "card_id"], rel_customer_card.values()),
        "rel_card_device.csv": (["card_id", "device_id"], rel_card_device.values()),
        "rel_card_payment.csv": (["card_id", "payment_id"], rel_card_payment.values()),
        "rel_payment_merchant.csv": (["payment_id", "merchant_id"], rel_payment_merchant.values()),
    }

    export_dir = EXPORT_ROOT / safe_graph
    import_dir = NEO4J_IMPORT_ROOT / safe_graph
    _write_csvs(export_dir, datasets)
    _write_csvs(import_dir, datasets)

    return {
        "rows": len(rows),
        "customers": len(customers),
        "cards": len(cards),
        "devices": len(devices),
        "merchants": len(merchants),
        "payments": len(payments),
    }


def load_graph_into_neo4j(graph_name: str) -> None:
    safe_graph = _validate_identifier(graph_name, "graph_name")
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "neo4j_password")),
    )
    statements = [
        "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.customer_id IS UNIQUE",
        "CREATE CONSTRAINT card_id IF NOT EXISTS FOR (c:Card) REQUIRE c.card_id IS UNIQUE",
        "CREATE CONSTRAINT device_id IF NOT EXISTS FOR (d:Device) REQUIRE d.device_id IS UNIQUE",
        "CREATE CONSTRAINT merchant_id IF NOT EXISTS FOR (m:Merchant) REQUIRE m.merchant_id IS UNIQUE",
        "CREATE CONSTRAINT payment_id IF NOT EXISTS FOR (p:Payment) REQUIRE p.payment_id IS UNIQUE",
        f"MATCH (p:Payment {{graph_name: '{safe_graph}'}}) DETACH DELETE p",
        f"""
        LOAD CSV WITH HEADERS FROM 'file:///{safe_graph}/customers.csv' AS row
        MERGE (:Customer {{customer_id: row.customer_id}})
        """,
        f"""
        LOAD CSV WITH HEADERS FROM 'file:///{safe_graph}/cards.csv' AS row
        MERGE (:Card {{card_id: row.card_id}})
        """,
        f"""
        LOAD CSV WITH HEADERS FROM 'file:///{safe_graph}/devices.csv' AS row
        MERGE (:Device {{device_id: row.device_id}})
        """,
        f"""
        LOAD CSV WITH HEADERS FROM 'file:///{safe_graph}/merchants.csv' AS row
        MERGE (m:Merchant {{merchant_id: row.merchant_id}})
        SET m.country = row.country, m.mcc = row.mcc
        """,
        f"""
        LOAD CSV WITH HEADERS FROM 'file:///{safe_graph}/payments.csv' AS row
        MERGE (p:Payment {{payment_id: row.payment_id}})
        SET
          p.payment_group_id = row.payment_group_id,
          p.event_time = row.event_time,
          p.amount = toFloat(row.amount),
          p.currency = row.currency,
          p.status = row.status,
          p.country = row.country,
          p.risk_score = toInteger(row.risk_score),
          p.reasons = row.reasons,
          p.is_alert = CASE row.is_alert WHEN 'True' THEN true ELSE false END,
          p.ip = row.ip,
          p.graph_name = row.graph_name
        """,
        f"""
        LOAD CSV WITH HEADERS FROM 'file:///{safe_graph}/rel_customer_card.csv' AS row
        MATCH (customer:Customer {{customer_id: row.customer_id}})
        MATCH (card:Card {{card_id: row.card_id}})
        MERGE (customer)-[:OWNS_CARD]->(card)
        """,
        f"""
        LOAD CSV WITH HEADERS FROM 'file:///{safe_graph}/rel_card_device.csv' AS row
        MATCH (card:Card {{card_id: row.card_id}})
        MATCH (device:Device {{device_id: row.device_id}})
        MERGE (card)-[:USED_ON]->(device)
        """,
        f"""
        LOAD CSV WITH HEADERS FROM 'file:///{safe_graph}/rel_card_payment.csv' AS row
        MATCH (card:Card {{card_id: row.card_id}})
        MATCH (payment:Payment {{payment_id: row.payment_id}})
        MERGE (card)-[:AUTHORIZED]->(payment)
        """,
        f"""
        LOAD CSV WITH HEADERS FROM 'file:///{safe_graph}/rel_payment_merchant.csv' AS row
        MATCH (payment:Payment {{payment_id: row.payment_id}})
        MATCH (merchant:Merchant {{merchant_id: row.merchant_id}})
        MERGE (payment)-[:AT_MERCHANT]->(merchant)
        """,
    ]

    with driver.session() as session:
        for statement in statements:
            session.run(statement).consume()
    driver.close()
