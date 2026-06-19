FROM python:3.11-slim
WORKDIR /app

RUN ln -s /usr/local/bin/python3 /usr/local/bin/python || true

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/       ./app/
COPY scripts/   ./scripts/
COPY data/      ./data/
COPY ml/        ./ml/
COPY alembic/   ./alembic/
COPY alembic.ini .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
