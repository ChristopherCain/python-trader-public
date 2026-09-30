from pythontrader.storage.sqlite import SQLiteStore


def test_sqlite(tmp_path):
    s = SQLiteStore(str(tmp_path / "x.db"))
    s.append(1.0, "x", {"a": 1})
    assert s.tail(1)[0][1] == "x"
