"""Duplicate injector — creates 500 near-duplicate records to train entity resolution."""
from __future__ import annotations
import random
import uuid
from pathlib import Path

import pandas as pd

random.seed(42)

NICKNAME_MAP = {
    "william": "bill", "elizabeth": "liz", "michael": "mike", "robert": "rob",
    "richard": "rick", "christopher": "chris", "jennifer": "jen", "katherine": "kate",
    "thomas": "tom", "james": "jim", "joseph": "joe", "patricia": "pat",
    "timothy": "tim", "daniel": "dan", "anthony": "tony", "margaret": "peggy",
    "barbara": "barb", "dorothy": "dot", "stephen": "steve", "edward": "ed",
    "harold": "harry", "donald": "don", "raymond": "ray", "gerald": "jerry",
    "lawrence": "larry", "samuel": "sam", "benjamin": "ben", "charles": "charlie",
    "frederick": "fred", "alexandra": "alex",
}


def _name_casing_variation(row: dict) -> dict:
    r = dict(row)
    r["first_name"] = str(r.get("first_name", "") or "").upper()
    r["last_name"] = str(r.get("last_name", "") or "").upper()
    return r, "first_name"


def _name_abbreviation(row: dict) -> dict:
    r = dict(row)
    fn = str(r.get("first_name", "") or "")
    if len(fn) > 1:
        r["first_name"] = fn[0] + "."
    return r, "first_name"


def _address_format(row: dict) -> dict:
    r = dict(row)
    addr = str(r.get("address_line1", "") or "")
    addr = addr.replace("Street", "St").replace("Avenue", "Ave").replace("Drive", "Dr")
    r["address_line1"] = addr
    return r, "address_line1"


def _phone_format(row: dict) -> dict:
    r = dict(row)
    phone = str(r.get("phone", "") or "")
    digits = "".join(c for c in phone if c.isdigit())[-10:]
    if len(digits) == 10:
        r["phone"] = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return r, "phone"


def _nickname(row: dict) -> dict:
    r = dict(row)
    fn = str(r.get("first_name", "") or "").lower()
    if fn in NICKNAME_MAP:
        r["first_name"] = NICKNAME_MAP[fn].title()
    elif fn in NICKNAME_MAP.values():
        reverse = {v: k for k, v in NICKNAME_MAP.items()}
        r["first_name"] = reverse.get(fn, r["first_name"]).title()
    return r, "first_name"


VARIATION_FNS = [_name_casing_variation, _name_abbreviation, _address_format, _phone_format, _nickname]


def inject_duplicates(source_dir: str, n_duplicates: int = 500, output_dir: str = None) -> dict:
    src = Path(source_dir)
    out = Path(output_dir or source_dir)

    dfs = {}
    for name in ("crm_records", "kyc_records", "cbs_records", "risk_records"):
        path = src / f"{name}.csv"
        if path.exists():
            dfs[name] = pd.read_csv(path)

    if not dfs:
        print("No source CSV files found — skipping duplicate injection")
        return {"duplicates_created": 0, "by_type": {}, "ground_truth_path": ""}

    # Find customers that appear in multiple source files
    all_customer_ids: list[str] = []
    for df in dfs.values():
        if "customer_id" in df.columns:
            all_customer_ids.extend(df["customer_id"].tolist())

    from collections import Counter
    multi_source = [cid for cid, cnt in Counter(all_customer_ids).items() if cnt >= 2]

    if not multi_source:
        multi_source = list(set(all_customer_ids))

    n_duplicates = min(n_duplicates, len(multi_source))
    sampled = random.sample(multi_source, n_duplicates)

    ground_truth = []
    by_type: dict[str, int] = {fn.__name__: 0 for fn in VARIATION_FNS}

    for i, cid in enumerate(sampled):
        var_fn = VARIATION_FNS[i % len(VARIATION_FNS)]
        type_name = var_fn.__name__

        # Find a source file that has this customer
        source_name = None
        original_row = None
        for sname, df in dfs.items():
            if "customer_id" not in df.columns:
                continue
            match = df[df["customer_id"] == cid]
            if not match.empty:
                source_name = sname
                original_row = match.iloc[0].to_dict()
                original_ext_id = str(original_row.get("external_id", ""))
                break

        if not original_row or not source_name:
            continue

        varied_row, varied_field = var_fn(original_row)
        new_ext_id = f"{original_ext_id}-DUP{i:03d}"
        varied_row["external_id"] = new_ext_id

        dfs[source_name] = pd.concat(
            [dfs[source_name], pd.DataFrame([varied_row])], ignore_index=True
        )
        by_type[type_name] = by_type.get(type_name, 0) + 1
        ground_truth.append({
            "base_customer_id": cid,
            "source_record_id_a": original_ext_id,
            "source_record_id_b": new_ext_id,
            "variation_type": type_name,
            "varied_field": varied_field,
        })

    # Write back updated source files
    for name, df in dfs.items():
        df.to_csv(out / f"{name}.csv", index=False)

    gt_path = str(out / "duplicate_ground_truth.csv")
    pd.DataFrame(ground_truth).to_csv(gt_path, index=False)
    print(f"Injected {len(ground_truth)} duplicate variants → {gt_path}")
    return {"duplicates_created": len(ground_truth), "by_type": by_type, "ground_truth_path": gt_path}
