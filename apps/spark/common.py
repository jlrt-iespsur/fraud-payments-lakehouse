from __future__ import annotations

import os

from pyspark.sql import SparkSession
from pyspark.sql.types import BooleanType, DoubleType, IntegerType, StringType, StructField, StructType


ICEBERG_CATALOG = os.getenv("ICEBERG_CATALOG", "lakehouse")
ICEBERG_DATABASE = os.getenv("ICEBERG_DATABASE", "payments")
ICEBERG_WAREHOUSE = os.getenv("ICEBERG_WAREHOUSE", "s3://lakehouse/warehouse")
ICEBERG_JDBC_URI = os.getenv("ICEBERG_JDBC_URI", "jdbc:postgresql://postgres:5432/platform")
ICEBERG_JDBC_USER = os.getenv("ICEBERG_JDBC_USER", "lakehouse")
ICEBERG_JDBC_PASSWORD = os.getenv("ICEBERG_JDBC_PASSWORD", "lakehouse")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minio")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minio123")
S3_REGION = os.getenv("AWS_REGION", os.getenv("S3_REGION", "us-east-1"))


BRONZE_SCHEMA = StructType(
    [
        StructField("event_time", StringType(), False),
        StructField("payment_id", StringType(), False),
        StructField("payment_group_id", StringType(), True),
        StructField("customer_id", StringType(), False),
        StructField("card_id", StringType(), False),
        StructField("merchant_id", StringType(), False),
        StructField("device_id", StringType(), False),
        StructField("ip", StringType(), False),
        StructField("country", StringType(), False),
        StructField("amount", DoubleType(), False),
        StructField("currency", StringType(), False),
        StructField("status", StringType(), False),
        StructField("mcc", StringType(), False),
        StructField("attempt_number", IntegerType(), True),
        StructField("scenario", StringType(), True),
    ]
)


def table_name(name: str) -> str:
    return f"{ICEBERG_CATALOG}.{ICEBERG_DATABASE}.{name}"


def build_spark_session(app_name: str) -> SparkSession:
    os.environ.setdefault("AWS_REGION", S3_REGION)
    os.environ.setdefault("AWS_DEFAULT_REGION", S3_REGION)
    spark = (
        SparkSession.builder.appName(app_name)
        .config(
            f"spark.sql.catalog.{ICEBERG_CATALOG}",
            "org.apache.iceberg.spark.SparkCatalog",
        )
        .config(
            f"spark.sql.catalog.{ICEBERG_CATALOG}.catalog-impl",
            "org.apache.iceberg.jdbc.JdbcCatalog",
        )
        .config(f"spark.sql.catalog.{ICEBERG_CATALOG}.uri", ICEBERG_JDBC_URI)
        .config(f"spark.sql.catalog.{ICEBERG_CATALOG}.warehouse", ICEBERG_WAREHOUSE)
        .config(f"spark.sql.catalog.{ICEBERG_CATALOG}.jdbc.user", ICEBERG_JDBC_USER)
        .config(
            f"spark.sql.catalog.{ICEBERG_CATALOG}.jdbc.password",
            ICEBERG_JDBC_PASSWORD,
        )
        .config(
            f"spark.sql.catalog.{ICEBERG_CATALOG}.io-impl",
            "org.apache.iceberg.aws.s3.S3FileIO",
        )
        .config(f"spark.sql.catalog.{ICEBERG_CATALOG}.s3.endpoint", S3_ENDPOINT)
        .config(f"spark.sql.catalog.{ICEBERG_CATALOG}.s3.path-style-access", "true")
        .config(
            f"spark.sql.catalog.{ICEBERG_CATALOG}.s3.access-key-id",
            S3_ACCESS_KEY,
        )
        .config(
            f"spark.sql.catalog.{ICEBERG_CATALOG}.s3.secret-access-key",
            S3_SECRET_KEY,
        )
        .config(f"spark.sql.catalog.{ICEBERG_CATALOG}.s3.region", S3_REGION)
        .config(
            "spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
        )
        .config("spark.driver.extraJavaOptions", f"-Daws.region={S3_REGION}")
        .config("spark.executor.extraJavaOptions", f"-Daws.region={S3_REGION}")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def ensure_namespace(spark: SparkSession) -> None:
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {ICEBERG_CATALOG}.{ICEBERG_DATABASE}")


def bronze_columns_sql() -> str:
    return """
    event_time STRING,
    payment_id STRING,
    payment_group_id STRING,
    customer_id STRING,
    card_id STRING,
    merchant_id STRING,
    device_id STRING,
    ip STRING,
    country STRING,
    amount DOUBLE,
    currency STRING,
    status STRING,
    mcc STRING,
    attempt_number INT,
    scenario STRING,
    ingestion_ts TIMESTAMP
    """.strip()
