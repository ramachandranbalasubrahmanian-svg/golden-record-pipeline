.PHONY: venv db data pipeline train dev setup dump stop clean reset test

# ─── Environment ──────────────────────────────────────────────────────────────

venv:
	@echo "Creating Python virtual environment..."
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@echo "✅ Virtual env ready. Run: source .venv/bin/activate"

# ─── Database (the ONLY Docker part) ──────────────────────────────────────────

db:
	@echo "Starting PostgreSQL + pgvector (Docker)..."
	docker-compose up -d db
	@echo "Waiting for DB to be ready..."
	@until docker exec golden_record_db pg_isready -U postgres -d golden_record > /dev/null 2>&1; do \
		printf "."; sleep 1; \
	done
	@echo ""
	@echo "✅ Database ready on localhost:5432"

stop:
	@echo "Stopping database container..."
	docker-compose stop db
	@echo "✅ DB stopped (data preserved)"

# ─── Pipeline (all run natively) ──────────────────────────────────────────────

data:
	@echo "Generating synthetic data (~5 min)..."
	python data/generate_all.py

pipeline:
	@echo "Running pipeline scripts 01–05 (~30 min)..."
	python scripts/run_all.py

train:
	@echo "Training entity resolution model (~2 min)..."
	python ml/train_er_model.py

# ─── API ──────────────────────────────────────────────────────────────────────

dev:
	@echo "Starting FastAPI at http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ─── Full Setup (run once) ────────────────────────────────────────────────────

setup:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo " Golden Record Pipeline — Full Setup (Option A)"
	@echo " Estimated time: ~35 minutes"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(MAKE) db
	@$(MAKE) data
	@$(MAKE) pipeline
	@$(MAKE) train
	@echo ""
	@echo "🎉 Setup complete!"
	@echo "   Run: make dev     → start the API"
	@echo "   Run: make dump    → export DB for Railway"

# ─── Railway Export ───────────────────────────────────────────────────────────

dump:
	@echo "Exporting database for Railway deployment..."
	docker exec golden_record_db pg_dump -U postgres -Fc golden_record > ../golden_record_demo.dump
	@echo "✅ Exported: golden_record_demo.dump"

# ─── Testing ──────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v --tb=short

# ─── Cleanup ──────────────────────────────────────────────────────────────────

clean:
	@echo "Stopping and removing database (all data will be lost)..."
	docker-compose down -v
	@echo "Removing generated data files..."
	rm -rf data/raw/
	rm -f ml/er_model.pkl ml/er_metrics.json
	@echo "✅ Clean. Run 'make setup' to rebuild."

reset: clean setup
