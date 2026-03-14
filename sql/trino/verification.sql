SHOW SCHEMAS FROM iceberg;
SHOW TABLES FROM iceberg.payments;

SELECT count(*) AS bronze_rows
FROM iceberg.payments.bronze_payments;

SELECT count(*) AS silver_rows
FROM iceberg.payments.silver_payments;

SELECT count(*) AS alert_rows
FROM iceberg.payments.fraud_alerts;

SELECT *
FROM iceberg.payments.fraud_alerts
ORDER BY risk_score DESC
LIMIT 20;
