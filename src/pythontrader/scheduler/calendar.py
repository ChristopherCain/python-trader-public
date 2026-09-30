from datetime import UTC, datetime, time


class TradingCalendar:
    def __init__(self, open_time=time(13, 30), close_time=time(20, 0)):
        self.open_time = open_time
        self.close_time = close_time

    def is_open(self, ts: float) -> bool:
        d = datetime.fromtimestamp(ts, UTC)
        if d.weekday() >= 5:
            return False
        t = d.time().replace(tzinfo=None)
        return self.open_time <= t < self.close_time
