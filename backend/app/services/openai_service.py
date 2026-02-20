import json
import logging
from datetime import datetime, timezone

from app.config import get_settings
from app.schemas.macro_risk import MacroFactor, MacroRiskResponse

logger = logging.getLogger(__name__)

MODEL = "gpt-5.1"

SYSTEM_PROMPT = """You are a macro-economic analyst. Given a company's profile, recent news, and key financial metrics, identify the most important macro tailwinds and headwinds affecting this stock.

Respond ONLY with valid JSON in this exact format:
{
  "tailwinds": [
    {
      "title": "Short descriptive title",
      "explanation": "2-3 sentence explanation of the macro factor and how it specifically impacts this company",
      "impact": "high|medium|low",
      "category": "trade|rates|regulation|technology|geopolitical|commodity|consumer|labor|other"
    }
  ],
  "headwinds": [
    {
      "title": "Short descriptive title",
      "explanation": "2-3 sentence explanation",
      "impact": "high|medium|low",
      "category": "trade|rates|regulation|technology|geopolitical|commodity|consumer|labor|other"
    }
  ],
  "summary": "1-2 sentence overall macro outlook for this company"
}

Rules:
- Provide 3-5 tailwinds and 3-5 headwinds
- Focus on current, real macro factors (interest rates, trade policy, sector trends, regulation, geopolitics)
- Be specific to this company's sector and business model
- Impact levels: high = directly affects revenue/margins, medium = indirect but material, low = background factor
"""


class OpenAIService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.openai_api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import openai
            self._client = openai.AsyncOpenAI(api_key=self.api_key)
        return self._client

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_macro_risk(
        self,
        ticker: str,
        company_name: str | None = None,
        sector: str | None = None,
        market_cap: float | None = None,
        news_headlines: list[str] | None = None,
        metrics: dict | None = None,
    ) -> MacroRiskResponse | None:
        if not self.is_configured:
            return None

        # Build user prompt with company context
        parts = [f"Company: {company_name or ticker} ({ticker})"]
        if sector:
            parts.append(f"Sector: {sector}")
        if market_cap:
            cap_b = market_cap / 1e9
            parts.append(f"Market Cap: ${cap_b:.1f}B" if cap_b >= 1 else f"Market Cap: ${market_cap / 1e6:.0f}M")

        if metrics:
            metric_lines = []
            for k, v in metrics.items():
                if v is not None:
                    metric_lines.append(f"  {k}: {v}")
            if metric_lines:
                parts.append("Key Metrics:\n" + "\n".join(metric_lines))

        if news_headlines:
            parts.append("Recent News Headlines:\n" + "\n".join(f"  - {h}" for h in news_headlines[:10]))

        user_prompt = "\n\n".join(parts)

        try:
            response = await self.client.chat.completions.create(
                model=MODEL,
                max_tokens=1500,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )

            raw = response.choices[0].message.content
            data = json.loads(raw)

            tailwinds = [MacroFactor(**f) for f in data.get("tailwinds", [])]
            headwinds = [MacroFactor(**f) for f in data.get("headwinds", [])]
            summary = data.get("summary", "")

            return MacroRiskResponse(
                ticker=ticker,
                company_name=company_name,
                sector=sector,
                tailwinds=tailwinds,
                headwinds=headwinds,
                summary=summary,
                analyzed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                model_used=MODEL,
            )

        except Exception as e:
            logger.error(f"OpenAI API error for {ticker}: {e}")
            return None
