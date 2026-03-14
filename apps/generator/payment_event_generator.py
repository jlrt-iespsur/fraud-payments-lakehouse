from __future__ import annotations

import argparse
import json
import random
import time
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Deque

from kafka import KafkaProducer


COUNTRIES = ["ES", "PT", "FR", "IT", "DE", "GB", "US", "MX"]
CURRENCIES = {
    "ES": "EUR",
    "PT": "EUR",
    "FR": "EUR",
    "IT": "EUR",
    "DE": "EUR",
    "GB": "GBP",
    "US": "USD",
    "MX": "MXN",
}
MCCS = ["5411", "5732", "5812", "4111", "4900", "5999", "5651", "5942"]


@dataclass(frozen=True)
class CustomerProfile:
    customer_id: str
    card_id: str
    merchant_home: str
    device_id: str
    country: str


def build_profiles(size: int) -> list[CustomerProfile]:
    profiles: list[CustomerProfile] = []
    for idx in range(size):
        country = random.choice(COUNTRIES[:5])
        profiles.append(
            CustomerProfile(
                customer_id=f"cust-{idx:04d}",
                card_id=f"card-{idx:04d}",
                merchant_home=f"merchant-{random.randint(1, 50):04d}",
                device_id=f"device-{random.randint(1, max(40, size // 3)):04d}",
                country=country,
            )
        )
    return profiles


def iso_now(offset_seconds: int = 0) -> str:
    now = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return now.replace(microsecond=0).isoformat()


def random_ip() -> str:
    return ".".join(str(random.randint(1, 254)) for _ in range(4))


def choose_amount(suspicious: bool = False) -> float:
    if suspicious:
        return round(random.uniform(700, 2800), 2)
    return round(random.triangular(3, 350, 45), 2)


def build_normal_event(profile: CustomerProfile) -> dict[str, object]:
    merchant_country = profile.country if random.random() < 0.9 else random.choice(COUNTRIES[:6])
    return {
        "event_time": iso_now(),
        "payment_id": f"pay-{uuid.uuid4().hex[:20]}",
        "payment_group_id": f"grp-{uuid.uuid4().hex[:12]}",
        "customer_id": profile.customer_id,
        "card_id": profile.card_id,
        "merchant_id": f"merchant-{random.randint(1, 120):04d}",
        "device_id": profile.device_id,
        "ip": random_ip(),
        "country": merchant_country,
        "amount": choose_amount(False),
        "currency": CURRENCIES.get(merchant_country, "EUR"),
        "status": "approved" if random.random() < 0.93 else "declined",
        "mcc": random.choice(MCCS),
        "attempt_number": 1,
        "scenario": "normal",
    }


def build_retry_event(base_event: dict[str, object]) -> dict[str, object]:
    event = dict(base_event)
    event["event_time"] = iso_now(random.randint(5, 90))
    event["payment_id"] = f"pay-{uuid.uuid4().hex[:20]}"
    event["status"] = "approved" if random.random() < 0.55 else "declined"
    event["attempt_number"] = int(base_event.get("attempt_number", 1)) + 1
    event["scenario"] = "retry"
    return event


def build_suspicious_event(profile: CustomerProfile) -> dict[str, object]:
    suspicious_country = random.choice(COUNTRIES)
    return {
        "event_time": iso_now(random.randint(0, 15)),
        "payment_id": f"pay-{uuid.uuid4().hex[:20]}",
        "payment_group_id": f"grp-{uuid.uuid4().hex[:12]}",
        "customer_id": profile.customer_id,
        "card_id": profile.card_id,
        "merchant_id": f"merchant-{random.randint(121, 180):04d}",
        "device_id": f"device-{random.randint(1, 18):04d}",
        "ip": random_ip(),
        "country": suspicious_country,
        "amount": choose_amount(True),
        "currency": CURRENCIES.get(suspicious_country, "EUR"),
        "status": "approved" if random.random() < 0.45 else "declined",
        "mcc": random.choice(MCCS),
        "attempt_number": 1,
        "scenario": "suspicious",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generador sintetico de pagos para Kafka")
    parser.add_argument("--bootstrap-servers", default="kafka:9092")
    parser.add_argument("--topic", default="payments")
    parser.add_argument("--events", type=int, default=1000)
    parser.add_argument("--sleep-ms", type=int, default=150)
    parser.add_argument("--profiles", type=int, default=250)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    profiles = build_profiles(args.profiles)
    producer = KafkaProducer(
        bootstrap_servers=args.bootstrap_servers,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        linger_ms=50,
        acks="all",
    )
    recent_declines: Deque[dict[str, object]] = deque(maxlen=1000)
    recent_events: Deque[dict[str, object]] = deque(maxlen=1000)

    for _ in range(args.events):
        profile = random.choice(profiles)
        selector = random.random()
        if selector < 0.72 or not recent_declines:
            event = build_normal_event(profile)
        elif selector < 0.85:
            event = build_retry_event(random.choice(list(recent_declines)))
        else:
            event = build_suspicious_event(profile)

        producer.send(args.topic, value=event, key=str(event["card_id"]).encode("utf-8"))
        recent_events.append(event)
        if event["status"] == "declined":
            recent_declines.append(event)

        # Metemos algún duplicado suelto para comprobar que Silver los limpia.
        if recent_events and random.random() < 0.02:
            duplicate = dict(random.choice(list(recent_events)))
            producer.send(args.topic, value=duplicate, key=str(duplicate["card_id"]).encode("utf-8"))

        time.sleep(args.sleep_ms / 1000)

    producer.flush()
    producer.close()


if __name__ == "__main__":
    main()
