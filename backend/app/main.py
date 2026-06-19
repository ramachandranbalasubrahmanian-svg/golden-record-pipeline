from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings
from app.database import get_db, init_db
from app.api import golden_records, rag_query, stewardship, lineage_api, gdpr


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Golden Record RAG Pipeline",
    version="1.0.0",
    description="Portfolio demo — Entity-resolved customer golden records with RAG query interface",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return api_key


app.include_router(golden_records.router, dependencies=[Depends(verify_api_key)])
app.include_router(rag_query.router, dependencies=[Depends(verify_api_key)])
app.include_router(stewardship.router, dependencies=[Depends(verify_api_key)])
app.include_router(lineage_api.router, dependencies=[Depends(verify_api_key)])
app.include_router(gdpr.router, dependencies=[Depends(verify_api_key)])


@app.get("/")
async def root():
    return {"service": "Golden Record API", "version": "1.0.0", "status": "healthy"}


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "db": str(e)}
