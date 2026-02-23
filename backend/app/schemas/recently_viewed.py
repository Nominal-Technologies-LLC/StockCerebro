from datetime import datetime

from pydantic import BaseModel


class RecentlyViewedRecord(BaseModel):
    ticker: str
    company_name: str | None = None
    grade: str | None = None
    signal: str | None = None
    score: float | None = None
    viewed_at: datetime


class RecordViewRequest(BaseModel):
    ticker: str
    company_name: str | None = None
    grade: str | None = None
    signal: str | None = None
    score: float | None = None
