import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import auth, stock, fundamental, technical, scorecard, news, earnings, macro_risk

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="StockCerebro API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(stock.router)
app.include_router(fundamental.router)
app.include_router(technical.router)
app.include_router(scorecard.router)
app.include_router(news.router)
app.include_router(earnings.router)
app.include_router(macro_risk.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "StockCerebro"}


@app.on_event("startup")
async def startup():
    from app.database import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logging.getLogger(__name__).info("Database tables created")
