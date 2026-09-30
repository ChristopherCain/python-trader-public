from __future__ import annotations

import json
from urllib.request import Request, urlopen


class JsonHttp:
    def __init__(self, timeout=4.0, user_agent="PythonTrader/1.0"):
        self.timeout = timeout
        self.user_agent = user_agent

    def get(self, url, headers=None):
        h = {"User-Agent": self.user_agent, "Accept": "application/json"}
        h.update(headers or {})
        with urlopen(Request(url, headers=h), timeout=self.timeout) as r:
            return json.loads(r.read().decode("utf-8"))
