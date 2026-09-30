# Development
Use Python 3.11 or newer. Install with `pip install -e .[dev]`, run `pytest`, and start the API with `uvicorn pythontrader.api.app:app --reload`. New strategy modules should remain pure functions over immutable feature snapshots where practical. Stateful logic belongs in agents, portfolio, risk, execution or storage, not inside transport adapters.
