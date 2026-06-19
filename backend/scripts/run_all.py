#!/usr/bin/env python3
"""
Run the complete Golden Record pipeline.
Usage: cd backend && python scripts/run_all.py
Duration: ~30 minutes total for 5K customers
"""
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = [
    ("01 — Seed Database",     "scripts/01_seed.py"),
    ("02 — Data Quality",      "scripts/02_dq.py"),
    ("03 — Entity Resolution", "scripts/03_er.py"),
    ("04 — Survivorship",      "scripts/04_survivorship.py"),
    ("05 — RAG Indexing",      "scripts/05_rag_index.py"),
]


def run_script(name: str, path: str) -> bool:
    print(f"\n{'=' * 60}")
    print(f"▶ {name}")
    print(f"{'=' * 60}")
    start = time.time()
    result = subprocess.run([sys.executable, path], cwd=Path(__file__).parent.parent)
    elapsed = time.time() - start
    if result.returncode != 0:
        print(f"❌ FAILED: {name} (after {elapsed:.1f}s)")
        return False
    print(f"✅ Done: {name} ({elapsed:.1f}s)")
    return True


if __name__ == "__main__":
    total_start = time.time()
    for name, path in SCRIPTS:
        if not run_script(name, path):
            print("\n⛔ Pipeline aborted.")
            sys.exit(1)
    total = time.time() - total_start
    print(f"\n🎉 Pipeline complete in {total / 60:.1f} minutes")
    print("Next steps:")
    print("  make dump      → export database for Railway")
    print("  make dev       → start FastAPI locally")
