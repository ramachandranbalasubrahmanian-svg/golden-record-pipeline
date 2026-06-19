"""
Master data generation script.
Run: cd backend && python data/generate_all.py
Output: data/raw/*.csv files
Estimated time: ~5 minutes for full dataset
"""
import sys
from pathlib import Path

# Allow imports from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.generators import customers, source_systems, duplicates, conflicts, transactions


def main():
    raw = Path(__file__).parent / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("Golden Record Pipeline — Synthetic Data Generator")
    print("=" * 60)

    print("\n[1/6] Generating 5,000 customers...")
    result = customers.generate(n=5000, output_path=str(raw / "customers_master.csv"))
    print(f"  ✓ {result['count']} customers | PEP: {len(result['pep_ids'])} | Sanctioned: {len(result['sanctioned_ids'])}")

    print("\n[2/6] Splitting customers into 4 source systems...")
    ss = source_systems.split_to_sources(
        customers_path=str(raw / "customers_master.csv"),
        output_dir=str(raw),
        crm_ratio=0.90, kyc_ratio=0.64, cbs_ratio=0.46, risk_ratio=0.60,
    )
    print(f"  ✓ CRM: {ss['crm']} | KYC: {ss['kyc']} | CBS: {ss['cbs']} | RISK: {ss['risk']}")

    print("\n[3/6] Injecting 500 duplicate variants...")
    dup_result = duplicates.inject_duplicates(
        source_dir=str(raw), n_duplicates=500, output_dir=str(raw)
    )
    print(f"  ✓ {dup_result['duplicates_created']} duplicates | by type: {dup_result['by_type']}")

    print("\n[4/6] Injecting 1,000 attribute conflicts...")
    conflict_result = conflicts.inject_conflicts(source_dir=str(raw), n_conflicts=1000)
    print(f"  ✓ {conflict_result['conflicts_injected']} conflicts | types: {conflict_result['types']}")

    print("\n[5/6] Generating 150,000 transactions...")
    transactions.generate(
        customers_path=str(raw / "customers_master.csv"),
        output_path=str(raw / "transactions.csv"),
        n_transactions=150000,
        days_history=90,
        suspicious_ratio=0.02,
    )

    print("\n[6/6] Summary:")
    import os
    total_records = 0
    for fname in raw.glob("*.csv"):
        import csv
        with open(fname) as f:
            n = sum(1 for _ in csv.reader(f)) - 1
        size_kb = os.path.getsize(fname) // 1024
        print(f"  {fname.name:<40} {n:>8} rows  {size_kb:>6} KB")
        if "transaction" not in fname.name:
            total_records += n

    print(f"\n✅ Data generation complete.")
    print(f"   Source records: ~{total_records:,}")


if __name__ == "__main__":
    main()
