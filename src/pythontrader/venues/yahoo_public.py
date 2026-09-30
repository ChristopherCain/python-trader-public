from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import quote
from urllib.request import Request, urlopen

from pythontrader.domain import Quote


@dataclass(frozen=True, slots=True)
class YahooPublicClient:
    """Read-only equity/ETF quote adapter using Yahoo's public chart endpoint.

    This adapter is intentionally market-data only. It normalizes the latest
    regular-market close into PythonTrader's Quote contract when a native L1
    bid/ask is not available from the endpoint.
    """

    timeout_s: float = 5.0
    user_agent: str = "Mozilla/5.0 PythonTrader/1.3"

    def quote(self, symbol: str) -> Quote:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?interval=1m&range=1d"
        request = Request(
            url, headers={"User-Agent": self.user_agent, "Accept": "application/json"}
        )
        with urlopen(request, timeout=self.timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
        result = payload.get("chart", {}).get("result") or []
        if not result:
            error = payload.get("chart", {}).get("error")
            raise RuntimeError(f"Yahoo quote unavailable for {symbol}: {error}")
        row = result[0]
        meta = row.get("meta", {})
        price = float(meta.get("regularMarketPrice") or meta.get("previousClose") or 0.0)
        if price <= 0:
            raise RuntimeError(f"invalid Yahoo market price for {symbol}")
        # Chart API is not an L1 book. Represent a zero-width reference quote
        # rather than fabricating spread or depth.
        return Quote(symbol=symbol, bid=price, ask=price, bid_size=0.0, ask_size=0.0, venue="yahoo")
