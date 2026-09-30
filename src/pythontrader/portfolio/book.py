from pythontrader.domain import Fill, Position, Side


class Portfolio:
    def __init__(self, cash: float):
        self.cash = float(cash)
        self.positions: dict[str, Position] = {}
        self.fees = 0.0

    def apply(self, fill: Fill) -> None:
        p = self.positions.setdefault(fill.symbol, Position(fill.symbol))
        signed = fill.qty * (1 if fill.side is Side.BUY else -1)
        old = p.qty
        if old == 0 or old * signed > 0:
            total = abs(old) * p.avg_price + fill.qty * fill.price
            p.qty = old + signed
            p.avg_price = total / abs(p.qty) if p.qty else 0.0
        else:
            closed = min(abs(old), fill.qty)
            direction = 1 if old > 0 else -1
            p.realized_pnl += closed * (fill.price - p.avg_price) * direction
            p.qty = old + signed
            if p.qty == 0:
                p.avg_price = 0.0
            elif old * p.qty < 0:
                p.avg_price = fill.price
        self.cash -= signed * fill.price + fill.fee
        self.fees += fill.fee

    def equity(self, marks: dict[str, float]) -> float:
        return self.cash + sum(p.qty * marks.get(s, p.avg_price) for s, p in self.positions.items())

    def gross(self, marks: dict[str, float]) -> float:
        return sum(abs(p.qty * marks.get(s, p.avg_price)) for s, p in self.positions.items())

    def net(self, marks: dict[str, float]) -> float:
        return sum(p.qty * marks.get(s, p.avg_price) for s, p in self.positions.items())
