from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CompanyCache(Base):
    __tablename__ = "company_cache"

    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255))
    sector: Mapped[str | None] = mapped_column(String(100))
    industry: Mapped[str | None] = mapped_column(String(200))
    market_cap: Mapped[float | None] = mapped_column()
    raw_info: Mapped[dict | None] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PriceCache(Base):
    __tablename__ = "price_cache"
    __table_args__ = (
        Index("ix_price_cache_lookup", "ticker", "interval", "period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20))
    interval: Mapped[str] = mapped_column(String(10))
    period: Mapped[str] = mapped_column(String(10))
    ohlcv_data: Mapped[dict | None] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FundamentalCache(Base):
    __tablename__ = "fundamental_cache"
    __table_args__ = (
        Index("ix_fundamental_cache_lookup", "ticker", "data_type", "source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20))
    data_type: Mapped[str] = mapped_column(String(50))  # income_statement, balance_sheet, etc.
    source: Mapped[str] = mapped_column(String(20))  # yfinance, finnhub, edgar
    data: Mapped[dict | None] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalysisCache(Base):
    __tablename__ = "analysis_cache"
    __table_args__ = (
        Index("ix_analysis_cache_lookup", "ticker", "analysis_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20))
    analysis_type: Mapped[str] = mapped_column(String(50))  # fundamental, technical_daily, scorecard
    data: Mapped[dict | None] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NewsCache(Base):
    __tablename__ = "news_cache"
    __table_args__ = (
        Index("ix_news_cache_lookup", "ticker", "source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(20))
    articles: Mapped[dict | None] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PeerCache(Base):
    __tablename__ = "peer_cache"

    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    peers: Mapped[dict | None] = mapped_column(JSONB)  # list of peer tickers + metrics
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
