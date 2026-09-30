from fastapi import FastAPI
from pydantic import BaseModel

from pythontrader.engine import TradingEngine
from pythontrader.marketdata.synthetic import SyntheticFeed
from pythontrader.settings import Settings

app = FastAPI(title="PythonTrader Control Plane", version="0.9.0")
engine = TradingEngine(Settings())
feed = SyntheticFeed(["AAPL", "MSFT", "NVDA", "EURUSD", "BTCUSD"])


class StepRequest(BaseModel):
    steps: int = 1


@app.get("/health")
def health():
    return {"ok": True, "service": "pythontrader", "mode": engine.settings.mode}


@app.get("/v1/state")
def state():
    return engine.snapshot()


@app.post("/v1/step")
def step(req: StepRequest):
    fills = 0
    for _ in range(max(1, min(req.steps, 10000))):
        for q in feed.step():
            fills += engine.on_quote(q) is not None
    return {"fills": fills, "state": engine.snapshot()}


@app.get("/v1/orders")
def orders():
    return [
        {
            "id": k,
            "symbol": v.order.symbol,
            "side": v.order.side,
            "qty": v.order.qty,
            "status": v.status,
        }
        for k, v in engine.orders.records.items()
    ]


from pythontrader.api.universal import router as universal_router

app.include_router(universal_router)
