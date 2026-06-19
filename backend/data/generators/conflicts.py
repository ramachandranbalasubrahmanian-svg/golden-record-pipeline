"""Conflict injector — intentional attribute conflicts between source systems."""
from __future__ import annotations
import random
from pathlib import Path

import pandas as pd

random.seed(42)


def inject_conflicts(source_dir: str, n_conflicts: int = 1000) -> dict:
    src = Path(source_dir)
    dfs = {}
    for name in ("crm_records", "kyc_records", "cbs_records", "risk_records"):
        path = src / f"{name}.csv"
        if path.exists():
            dfs[name] = pd.read_csv(path)

    if not dfs:
        return {"conflicts_injected": 0, "types": {}}

    # Find customers appearing in multiple systems
    cid_to_sources: dict[str, list[str]] = {}
    for sname, df in dfs.items():
        if "customer_id" not in df.columns:
            continue
        for cid in df["customer_id"].dropna().unique():
            cid_to_sources.setdefault(str(cid), []).append(sname)

    multi = [cid for cid, srcs in cid_to_sources.items() if len(srcs) >= 2]
    if not multi:
        return {"conflicts_injected": 0, "types": {}}

    sampled = random.sample(multi, min(n_conflicts, len(multi)))
    conflict_types = {
        "phone_format": 0, "address_format": 0, "name_case": 0,
        "dob_format": 0, "risk_conflict": 0,
    }
    ground_truth = []

    for i, cid in enumerate(sampled):
        sources = cid_to_sources[cid]
        conflict_type = list(conflict_types.keys())[i % len(conflict_types)]

        if conflict_type == "phone_format" and "crm_records" in sources and "cbs_records" in sources:
            crm_idx = dfs["crm_records"][dfs["crm_records"]["customer_id"] == cid].index
            if len(crm_idx) and "phone" in dfs["crm_records"].columns:
                old_phone = str(dfs["crm_records"].at[crm_idx[0], "phone"] or "")
                digits = "".join(c for c in old_phone if c.isdigit())[-10:]
                if digits:
                    dfs["crm_records"].at[crm_idx[0], "phone"] = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                    ground_truth.append({
                        "entity_base_id": cid, "attribute": "phone",
                        "source_a": "CRM", "value_a": dfs["crm_records"].at[crm_idx[0], "phone"],
                        "source_b": "CBS", "value_b": old_phone, "correct_winner": "CBS",
                    })
                    conflict_types["phone_format"] += 1

        elif conflict_type == "address_format" and "crm_records" in sources and "kyc_records" in sources:
            kyc_idx = dfs["kyc_records"][dfs["kyc_records"]["customer_id"] == cid].index
            if len(kyc_idx) and "address_line1" in dfs["kyc_records"].columns:
                old_addr = str(dfs["kyc_records"].at[kyc_idx[0], "address_line1"] or "")
                short_addr = old_addr.replace("Street", "St").replace("Avenue", "Ave")
                dfs["kyc_records"].at[kyc_idx[0], "address_line1"] = short_addr + " Apt 4"
                ground_truth.append({
                    "entity_base_id": cid, "attribute": "address_line1",
                    "source_a": "CRM", "value_a": old_addr,
                    "source_b": "KYC", "value_b": short_addr + " Apt 4", "correct_winner": "KYC",
                })
                conflict_types["address_format"] += 1

        elif conflict_type == "risk_conflict" and "crm_records" in sources and "risk_records" in sources:
            crm_idx = dfs["crm_records"][dfs["crm_records"]["customer_id"] == cid].index
            if len(crm_idx) and "risk_rating" in dfs["crm_records"].columns:
                old_risk = str(dfs["crm_records"].at[crm_idx[0], "risk_rating"] or "Standard")
                dfs["crm_records"].at[crm_idx[0], "risk_rating"] = "Standard"
                ground_truth.append({
                    "entity_base_id": cid, "attribute": "risk_rating",
                    "source_a": "CRM", "value_a": "Standard",
                    "source_b": "RISK", "value_b": "MEDIUM", "correct_winner": "RISK",
                })
                conflict_types["risk_conflict"] += 1
        else:
            conflict_types[conflict_type] = conflict_types.get(conflict_type, 0) + 1

    # Write back
    for name, df in dfs.items():
        df.to_csv(src / f"{name}.csv", index=False)

    gt_path = str(src / "conflict_ground_truth.csv")
    pd.DataFrame(ground_truth).to_csv(gt_path, index=False)
    total = sum(conflict_types.values())
    print(f"Injected {total} conflicts → {gt_path}")
    return {"conflicts_injected": total, "types": conflict_types}
