#!/bin/bash
# run_pipeline.sh — Run full golden record pipeline with error handling
set -e
LOG=/app/pipeline.log
exec > >(tee -a $LOG) 2>&1

echo "============================================================"
echo "Pipeline started: $(date)"
echo "============================================================"

run_step() {
    local step=$1
    local script=$2
    echo ""
    echo ">>> STEP $step: $script — $(date)"
    if python $script; then
        echo "<<< STEP $step PASSED"
    else
        echo "<<< STEP $step FAILED — check $LOG for details"
        exit 1
    fi
}

run_step 0 "data/generate_all.py"
run_step 1 "scripts/01_seed.py"
run_step 2 "scripts/02_dq.py"
run_step 3 "scripts/03_er.py"
run_step 4 "scripts/04_survivorship.py"
run_step "1b" "scripts/01_seed.py"
run_step 5 "scripts/05_rag_index.py"

echo ""
echo "============================================================"
echo "ALL STEPS COMPLETE: $(date)"
echo "============================================================"
