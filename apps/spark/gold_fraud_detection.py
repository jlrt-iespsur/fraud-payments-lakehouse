from __future__ import annotations

from pyspark.sql.functions import array, col, concat_ws, expr, lit, size, when

from common import build_spark_session, ensure_namespace, table_name


def main() -> None:
    spark = build_spark_session("gold-fraud-detection")
    ensure_namespace(spark)
    spark.conf.set("spark.sql.codegen.wholeStage", "false")
    spark.conf.set("spark.sql.adaptive.enabled", "false")

    silver = spark.table(table_name("silver_payments"))

    enriched = (
        silver.withColumn(
            "raw_reasons",
            array(
                when(col("tx_by_card_5m") >= 5, lit("high_card_velocity_5m")),
                when(col("distinct_merchants_10m") >= 4, lit("many_merchants_10m")),
                when(col("distinct_countries_1h") >= 3, lit("many_countries_1h")),
                when(col("distinct_cards_per_device") >= 4, lit("device_shared_by_cards")),
                when(col("declined_ratio_1h") >= 0.45, lit("high_declined_ratio_1h")),
                when(col("amount") >= 1200, lit("high_amount")),
            ),
        )
        .withColumn("reasons", expr("filter(raw_reasons, x -> x is not null)"))
        .withColumn(
            "risk_score",
            when(col("tx_by_card_5m") >= 5, 24).otherwise(0)
            + when(col("distinct_merchants_10m") >= 4, 18).otherwise(0)
            + when(col("distinct_countries_1h") >= 3, 18).otherwise(0)
            + when(col("distinct_cards_per_device") >= 4, 16).otherwise(0)
            + when(col("declined_ratio_1h") >= 0.45, 12).otherwise(0)
            + when(col("amount") >= 1200, 12).otherwise(0),
        )
        .withColumn("reasons_text", concat_ws(", ", col("reasons")))
        .withColumn("is_alert", size(col("reasons")) > 0)
        .drop("raw_reasons")
    )

    alerts = (
        enriched.filter(col("is_alert"))
        .select(
            "payment_id",
            "event_time",
            "customer_id",
            "card_id",
            "merchant_id",
            "device_id",
            "country",
            "amount",
            "currency",
            "status",
            "tx_by_card_5m",
            "distinct_merchants_10m",
            "distinct_countries_1h",
            "distinct_cards_per_device",
            "declined_ratio_1h",
            "risk_score",
            "reasons",
            "reasons_text",
        )
    )

    graph_dataset = enriched.select(
        "payment_id",
        "payment_group_id",
        "event_time",
        "customer_id",
        "card_id",
        "merchant_id",
        "device_id",
        "ip",
        "country",
        "amount",
        "currency",
        "status",
        "mcc",
        "scenario",
        "risk_score",
        "reasons",
        "reasons_text",
        "is_alert",
    )

    alerts.writeTo(table_name("fraud_alerts")).using("iceberg").createOrReplace()
    graph_dataset.writeTo(table_name("graph_payments")).using("iceberg").createOrReplace()
    spark.stop()


if __name__ == "__main__":
    main()
