// Dispositivos compartidos por multiples tarjetas.
MATCH (card:Card)-[:USED_ON]->(device:Device)
WITH device, collect(card.card_id) AS cards, count(*) AS total_cards
WHERE total_cards >= 3
RETURN device.device_id, total_cards, cards
ORDER BY total_cards DESC;

// Tarjetas usadas en multiples paises.
MATCH (card:Card)-[:AUTHORIZED]->(payment:Payment)
WITH card, collect(DISTINCT payment.country) AS countries, count(DISTINCT payment.country) AS total_countries
WHERE total_countries >= 3
RETURN card.card_id, total_countries, countries
ORDER BY total_countries DESC;

// Comercios conectados a multiples entidades sospechosas.
MATCH (customer:Customer)-[:OWNS_CARD]->(card:Card)-[:AUTHORIZED]->(payment:Payment {is_alert: true})-[:AT_MERCHANT]->(merchant:Merchant)
WITH merchant, count(DISTINCT customer) AS suspicious_customers, count(DISTINCT card) AS suspicious_cards
WHERE suspicious_customers >= 2 OR suspicious_cards >= 3
RETURN merchant.merchant_id, suspicious_customers, suspicious_cards
ORDER BY suspicious_customers DESC, suspicious_cards DESC;

// Posibles agrupaciones de comportamiento anomalo por dispositivo compartido.
MATCH (card:Card)-[:USED_ON]->(device:Device)<-[:USED_ON]-(other_card:Card)
MATCH (other_card)-[:AUTHORIZED]->(payment:Payment {is_alert: true})
WHERE card.card_id <> other_card.card_id
RETURN device.device_id, collect(DISTINCT other_card.card_id) AS cards, count(DISTINCT payment) AS alert_payments
ORDER BY alert_payments DESC;
