import json
import sqlite3
from pathlib import Path


class SQLiteStore:
    def __init__(self, path: str = "pythontrader.db"):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "create table if not exists events(id integer primary key, ts real, topic text, payload text)"
        )
        self.conn.execute("create index if not exists idx_events_topic_ts on events(topic,ts)")
        self.conn.commit()

    def append(self, ts: float, topic: str, payload: dict):
        self.conn.execute(
            "insert into events(ts,topic,payload) values(?,?,?)", (ts, topic, json.dumps(payload))
        )
        self.conn.commit()

    def tail(self, limit: int = 100):
        return self.conn.execute(
            "select ts,topic,payload from events order by id desc limit ?", (limit,)
        ).fetchall()
