"""Transaction generator — 150,000 banking transactions with suspicious patterns."""
from __future__ import annotations
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
random.seed(42)
np.random.seed(42)

TX_TYPES = ["transfer", "payment", "withdrawal", "deposit", "wire", "fx_conversion"]
TX_TYPE_WEIGHTS = [0.25, 0.30, 0.15, 0.15, 0.10, 0.05]
CHANNELS = ["online", "mobile", "branch", "atm", "api"]
CHANNEL_WEIGHTS = [0.35, 0.30, 0.15, 0.15, 0.05]
CURRENCIES = ["USD", "EUR", "GBP", "OTHER"]
CURRENCY_WEIGHTS = [0.85, 0.10, 0.03, 0.02]
HIGH_RISK_COUNTRIES = ["IR", "KP", "CU", "SY", "BY"]
DOMESTIC_COUNTRIES = ["US", "GB", "DE", "SG"]


def generate(
    customers_path: str,
    output_path: str,
    n_transactions: int = 150000,
    days_history: int = 90,
    suspicious_ratio: float = 0.02,
) -> str:
    customers = pd.read_csv(customers_path)
    now = datetime.utcnow()
    start_date = now - timedelta(days=days_history)

    risk_weight_map = {"LOW": 1.0, "MEDIUM": 1.5, "HIGH": 2.5, "CRITICAL": 4.0}
    weights = customers["risk_rating"].map(risk_weight_map).fillna(1.0)
    pep_mask = customers["is_pep"].fillna(False)
    weights = weights * np.where(pep_mask, 1.5, 1.0)
    weights = weights / weights.sum()

    tx_counts = np.random.multinomial(n_transactions, weights)

    rows = []
    for idx, (_, cust) in enumerate(customers.iterrows()):
        cnt = tx_counts[idx]
        cid = str(cust["customer_id"])
        for _ in range(cnt):
            # Weight recent 30 days more
            if random.random() < 0.70:
                dt = now - timedelta(days=random.uniform(0, 30))
            else:
                dt = start_date + timedelta(days=random.uniform(0, days_history))

            amount = round(np.random.lognormal(6.5, 1.8), 2)
            c_country = random.choices(
                DOMESTIC_COUNTRIES + ["other"], weights=[0.2, 0.2, 0.2, 0.2, 0.2]
            )[0]
            if c_country == "other":
                c_country = fake.country_code()

            rows.append({
                "transaction_id": str(uuid.uuid4()),
                "customer_id": cid,
                "transaction_date": dt.isoformat(),
                "amount": amount,
                "currency": random.choices(CURRENCIES, CURRENCY_WEIGHTS)[0],
                "transaction_type": random.choices(TX_TYPES, TX_TYPE_WEIGHTS)[0],
                "channel": random.choices(CHANNELS, CHANNEL_WEIGHTS)[0],
                "counterparty_name": fake.company(),
                "counterparty_country": c_country,
                "is_suspicious": False,
                "suspicious_reason": None,
            })

    df = pd.DataFrame(rows)

    # Pattern A — Structuring (500 tx)
    high_risk_custs = customers[customers["risk_rating"].isin(["HIGH", "CRITICAL"])]["customer_id"].tolist()
    structuring_custs = random.sample(high_risk_custs[:50], min(20, len(high_risk_custs)))
    for cid in structuring_custs:
        for _ in range(25):
            dt = now - timedelta(days=random.uniform(0, 30))
            idx = df[df["customer_id"] == cid].index
            if len(idx):
                df.at[idx[0], "is_suspicious"] = True
                df.at[idx[0], "suspicious_reason"] = "STRUCTURING: Multiple transactions just below $10K threshold"
                df.at[idx[0], "amount"] = 9500.00

    # Pattern B — High-risk jurisdiction wires (1000 tx)
    all_custs = customers["customer_id"].tolist()
    wire_custs = random.sample(all_custs, min(100, len(all_custs)))
    for cid in wire_custs:
        idx_list = df[df["customer_id"] == cid].index[:10]
        for i in idx_list:
            df.at[i, "is_suspicious"] = True
            country = random.choice(HIGH_RISK_COUNTRIES)
            df.at[i, "suspicious_reason"] = f"WIRE_TO_HIGH_RISK_JURISDICTION: {country}"
            df.at[i, "counterparty_country"] = country
            df.at[i, "amount"] = round(random.uniform(5000, 250000), 2)

    # Pattern C — Rapid movement
    rapid_custs = random.sample(all_custs, min(50, len(all_custs)))
    for cid in rapid_custs:
        idx_list = df[df["customer_id"] == cid].index[:20]
        for i in idx_list:
            df.at[i, "is_suspicious"] = True
            df.at[i, "suspicious_reason"] = "RAPID_MOVEMENT: High velocity in 72h window"

    # Pattern D — PEP large cash
    pep_custs = customers[customers["is_pep"] == True]["customer_id"].tolist()
    for cid in pep_custs:
        idx_list = df[df["customer_id"] == cid].index[:3]
        for i in idx_list:
            df.at[i, "is_suspicious"] = True
            df.at[i, "suspicious_reason"] = "PEP_LARGE_CASH: PEP customer high-value cash transaction"
            df.at[i, "amount"] = round(random.uniform(50000, 500000), 2)
            df.at[i, "channel"] = "branch"
            df.at[i, "transaction_type"] = random.choice(["withdrawal", "deposit"])

    suspicious = int(df["is_suspicious"].sum())
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} transactions ({suspicious} suspicious) → {output_path}")
    return output_path
