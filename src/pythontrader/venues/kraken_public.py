from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pythontrader.domain import Quote


@dataclass(frozen=True, slots=True)
class KrakenPublicClient:
    base_url: str = "https://api.kraken.com/0/public"
    timeout_s: float = 5.0
    user_agent: str = "PythonTrader/1.3"

    def _get(self, path: str, params: dict[str, str]) -> dict:
        url = f"{self.base_url}/{path}?{urlencode(params)}"
        request = Request(
            url, headers={"User-Agent": self.user_agent, "Accept": "application/json"}
        )
        with urlopen(request, timeout=self.timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
        errors = payload.get("error") or []
        if errors:
            raise RuntimeError(f"Kraken error: {', '.join(errors)}")
        return payload["result"]

    def quote(self, pair: str, *, symbol: str | None = None) -> Quote:
        result = self._get("Ticker", {"pair": pair})
        if not result:
            raise RuntimeError(f"no ticker returned for {pair}")
        row = next(iter(result.values()))
        bid = float(row["b"][0])
        ask = float(row["a"][0])
        bid_size = float(row["b"][2]) if len(row["b"]) > 2 else 0.0
        ask_size = float(row["a"][2]) if len(row["a"]) > 2 else 0.0
        if bid <= 0 or ask <= 0 or ask < bid:
            raise RuntimeError(f"invalid Kraken quote for {pair}: {bid}/{ask}")
        return Quote(
            symbol=symbol or pair,
            bid=bid,
            ask=ask,
            bid_size=bid_size,
            ask_size=ask_size,
            venue="kraken",
        )
