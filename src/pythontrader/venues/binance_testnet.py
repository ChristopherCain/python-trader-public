from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from time import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class TestnetOrderAck:
    symbol: str
    order_id: int
    client_order_id: str
    status: str
    side: str
    order_type: str


class BinanceSpotTestnetAdapter:
    """Minimal Binance Spot Test Network adapter.

    The default endpoint is testnet-only. Credentials are injected by the caller;
    this module never reads or stores secrets on disk.
    """

    def __init__(
        self,
        *,
        api_key: str = "",
        api_secret: str = "",
        base_url: str = "https://testnet.binance.vision",
        timeout_s: float = 5.0,
    ) -> None:
        if not base_url.startswith("https://testnet.binance.vision"):
            raise ValueError("adapter is restricted to Binance Spot Test Network")
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def _request(
        self, method: str, path: str, params: dict[str, Any] | None = None, *, signed: bool = False
    ) -> Any:
        values = dict(params or {})
        headers = {"Accept": "application/json"}
        if signed:
            if not self.api_key or not self.api_secret:
                raise ValueError("testnet API credentials are required for signed requests")
            values.setdefault("timestamp", int(time() * 1000))
            query = urlencode(values)
            signature = hmac.new(
                self.api_secret.encode(), query.encode(), hashlib.sha256
            ).hexdigest()
            values["signature"] = signature
            headers["X-MBX-APIKEY"] = self.api_key
        query = urlencode(values)
        url = f"{self.base_url}{path}" + (f"?{query}" if query else "")
        request = Request(url, method=method, headers=headers)
        with urlopen(request, timeout=self.timeout_s) as response:  # noqa: S310 - restricted testnet URL
            return json.loads(response.read().decode())

    def ping(self) -> bool:
        self._request("GET", "/api/v3/ping")
        return True

    def ticker(self, symbol: str) -> dict[str, Any]:
        return dict(self._request("GET", "/api/v3/ticker/bookTicker", {"symbol": symbol.upper()}))

    def place_limit(
        self, *, symbol: str, side: str, quantity: str, price: str, client_order_id: str
    ) -> TestnetOrderAck:
        payload = self._request(
            "POST",
            "/api/v3/order",
            {
                "symbol": symbol.upper(),
                "side": side.upper(),
                "type": "LIMIT",
                "timeInForce": "GTC",
                "quantity": quantity,
                "price": price,
                "newClientOrderId": client_order_id,
            },
            signed=True,
        )
        return TestnetOrderAck(
            str(payload["symbol"]),
            int(payload["orderId"]),
            str(payload.get("clientOrderId", client_order_id)),
            str(payload["status"]),
            str(payload["side"]),
            str(payload["type"]),
        )

    def cancel(self, *, symbol: str, client_order_id: str) -> dict[str, Any]:
        return dict(
            self._request(
                "DELETE",
                "/api/v3/order",
                {"symbol": symbol.upper(), "origClientOrderId": client_order_id},
                signed=True,
            )
        )

    def open_orders(self, *, symbol: str | None = None) -> list[dict[str, Any]]:
        params = {"symbol": symbol.upper()} if symbol else {}
        result = self._request("GET", "/api/v3/openOrders", params, signed=True)
        return [dict(item) for item in result]
