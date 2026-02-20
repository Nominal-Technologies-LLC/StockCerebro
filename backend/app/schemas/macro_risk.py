from typing import Literal

from pydantic import BaseModel


class MacroFactor(BaseModel):
    title: str
    explanation: str
    impact: Literal["high", "medium", "low"]
    category: str  # trade, rates, regulation, technology, geopolitical, commodity, consumer, labor, other


class MacroRiskResponse(BaseModel):
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    tailwinds: list[MacroFactor] = []
    headwinds: list[MacroFactor] = []
    summary: str = ""
    analyzed_at: str = ""
    model_used: str = ""
    error: str | None = None
