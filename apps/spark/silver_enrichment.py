from __future__ import annotations

from pyspark.sql import Window
from pyspark.sql.functions import (
    array_distinct,
    avg,
    col,
    collect_list,
    row_number,
    round,
    size,
    to_timestamp,
    when,
)

from common import build_spark_session, ensure_namespace, table_name


def main() -> None:
    spark = build_spark_session("silver-payments-batch")
    ensure_namespace(spark)

    bronze = spark.table(table_name("bronze_payments"))

    typed = (
        bronze.withColumn("event_time_ts", to_timestamp("event_time"))
        .withColumn("attempt_number", col("attempt_number").cast("int"))
        .withColumn("amount", col("amount").cast("double"))
        .filter(col("event_time_ts").isNotNull())
    )

    dedup_window = Window.partitionBy("payment_id").orderBy(col("ingestion_ts").desc())
    deduped = (
        typed.withColumn("row_num", row_number().over(dedup_window))
        .filter(col("row_num") == 1)
        .drop("row_num")
    )

    event_epoch = col("event_time_ts").cast("long")
    card_window_5m = Window.partitionBy("card_id").orderBy(event_epoch).rangeBetween(-300, 0)
    merchant_window_10m = Window.partitionBy("card_id").orderBy(event_epoch).rangeBetween(-600, 0)
    country_window_1h = Window.partitionBy("card_id").orderBy(event_epoch).rangeBetween(-3600, 0)
    device_window = Window.partitionBy("device_id")

    silver = (
        deduped.withColumn("tx_by_card_5m", size(collect_list("payment_id").over(card_window_5m)))
        .withColumn(
            "distinct_merchants_10m",
            size(array_distinct(collect_list("merchant_id").over(merchant_window_10m))),
        )
        .withColumn(
            "distinct_countries_1h",
            size(array_distinct(collect_list("country").over(country_window_1h))),
        )
        .withColumn(
            "distinct_cards_per_device",
            size(array_distinct(collect_list("card_id").over(device_window))),
        )
        .withColumn(
            "declined_ratio_1h",
            round(
                avg(when(col("status") == "declined", 1.0).otherwise(0.0)).over(country_window_1h),
                4,
            ),
        )
        .select(
            "event_time_ts",
            "payment_id",
            "payment_group_id",
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
            "attempt_number",
            "scenario",
            "ingestion_ts",
            "tx_by_card_5m",
            "distinct_merchants_10m",
            "distinct_countries_1h",
            "distinct_cards_per_device",
            "declined_ratio_1h",
        )
    )

    silver.createOrReplaceTempView("silver_source")
    spark.sql(
        f"""
        CREATE OR REPLACE TABLE {table_name("silver_payments")}
        USING iceberg
        AS
        SELECT
            event_time_ts AS event_time,
            payment_id,
            payment_group_id,
            customer_id,
            card_id,
            merchant_id,
            device_id,
            ip,
            country,
            amount,
            currency,
            status,
            mcc,
            attempt_number,
            scenario,
            ingestion_ts,
            tx_by_card_5m,
            distinct_merchants_10m,
            distinct_countries_1h,
            distinct_cards_per_device,
            declined_ratio_1h
        FROM silver_source
        """
    )
    spark.stop()


if __name__ == "__main__":
    main()
