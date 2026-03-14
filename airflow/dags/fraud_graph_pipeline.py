from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.python import PythonOperator

from orchestration.lakehouse_tasks import compact_table, export_graph_dataset, load_graph_into_neo4j


def compact_table_task(**context) -> None:
    compact_table(context["params"]["source_table"])


def export_graph_task(**context) -> dict[str, int]:
    params = context["params"]
    return export_graph_dataset(
        graph_name=params["graph_name"],
        start_ts=params.get("start_ts"),
        end_ts=params.get("end_ts"),
    )


def load_graph_task(**context) -> None:
    load_graph_into_neo4j(context["params"]["graph_name"])


with DAG(
    dag_id="fraud_graph_pipeline",
    description="Compactacion Iceberg y carga bajo demanda del grafo de fraude",
    start_date=datetime(2026, 3, 1),
    schedule=None,
    catchup=False,
    default_args={"owner": "codex", "retries": 1, "retry_delay": timedelta(minutes=2)},
    params={
        "source_table": Param("graph_payments", type="string"),
        "start_ts": Param("", type=["null", "string"]),
        "end_ts": Param("", type=["null", "string"]),
        "graph_name": Param("fraud_snapshot", type="string"),
    },
    tags=["fraud", "lakehouse", "neo4j"],
) as dag:
    compact = PythonOperator(
        task_id="compact_iceberg_table",
        python_callable=compact_table_task,
    )

    export = PythonOperator(
        task_id="export_graph_dataset",
        python_callable=export_graph_task,
    )

    load = PythonOperator(
        task_id="load_graph_to_neo4j",
        python_callable=load_graph_task,
    )

    compact >> export >> load
