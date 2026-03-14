from __future__ import annotations

import argparse
import time

from pyspark.sql.functions import col, current_timestamp, from_json

from common import BRONZE_SCHEMA, build_spark_session, bronze_columns_sql, ensure_namespace, table_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kafka -> Iceberg Bronze")
    parser.add_argument("--bootstrap-servers", default="kafka:9092")
    parser.add_argument("--topic", default="payments")
    parser.add_argument(
        "--checkpoint",
        default="/opt/project/runtime/checkpoints/bronze",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spark = build_spark_session("bronze-payments-stream")
    ensure_namespace(spark)

    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name("bronze_payments")} (
            {bronze_columns_sql()}
        )
        USING iceberg
        """
    )

    raw_stream = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", args.bootstrap_servers)
        .option("subscribe", args.topic)
        .option("startingOffsets", "earliest")
        .load()
    )

    parsed_stream = (
        raw_stream.select(from_json(col("value").cast("string"), BRONZE_SCHEMA).alias("payload"))
        .select("payload.*")
        .withColumn("ingestion_ts", current_timestamp())
    )

    query = (
        parsed_stream.writeStream.format("iceberg")
        .outputMode("append")
        .queryName("bronze_payments_stream")
        .option("checkpointLocation", args.checkpoint)
        .trigger(processingTime="5 seconds")
        .toTable(table_name("bronze_payments"))
    )
    print(f"Bronze streaming query iniciada: id={query.id}, run_id={query.runId}", flush=True)

    while query.isActive:
        time.sleep(5)

    exception = query.exception()
    if exception is not None:
        raise RuntimeError(f"La query Bronze se ha detenido con error: {exception}")
    raise RuntimeError("La query Bronze se ha detenido inesperadamente sin exponer una excepcion detallada.")


if __name__ == "__main__":
    main()
