from __future__ import annotations

from dataclasses import asdict

from pythontrader.execution.universal_router import UniversalExecutionPlanner
from pythontrader.intelligence.brain import TradingBrain
from pythontrader.universe.registry import InstrumentRegistry
from pythontrader.venues.synthetic import SyntheticUniversalVenue


class AutonomousTrader:
    def __init__(self, registry=None, venue=None):
        self.registry = registry or InstrumentRegistry()
        self.venue = venue or SyntheticUniversalVenue()
        self.brain = TradingBrain()
        self.planner = UniversalExecutionPlanner()
        self.iteration = 0
        self.decisions = []

    def features_from_quote(self, q, prev=None):
        momentum = 0.0 if not prev else q.mid / prev.mid - 1
        imbalance = (q.bid_size - q.ask_size) / max(1e-9, q.bid_size + q.ask_size)
        spread = q.spread / max(1e-9, q.mid)
        return {
            "momentum": momentum,
            "imbalance": imbalance,
            "volatility": abs(momentum) * 4,
            "zscore": momentum / max(1e-6, spread),
        }

    def scan_once(self):
        out = []
        prev = getattr(self, "_prev", {})
        now = {}
        for i in self.registry.all():
            q = self.venue.quote(i.symbol)
            now[i.symbol] = q
            f = self.features_from_quote(q, prev.get(i.symbol))
            d = self.brain.infer(f)
            plan = self.planner.plan(
                i, abs(d.score), q.spread / q.mid * 10000, f["volatility"], 10_000
            )
            row = {
                "symbol": i.symbol,
                "asset_class": i.asset_class.value,
                "venue": i.venue,
                "mid": q.mid,
                "action": d.action,
                "score": d.score,
                "confidence": d.confidence,
                "regime": d.regime,
                "execution": asdict(plan),
            }
            out.append(row)
        self._prev = now
        self.iteration += 1
        self.decisions = out
        return out

    def status(self):
        return {
            "iteration": self.iteration,
            "universe": len(self.registry.all()),
            "asset_classes": sorted({x.asset_class.value for x in self.registry.all()}),
            "decisions": self.decisions,
        }
