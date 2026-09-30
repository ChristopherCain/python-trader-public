from pythontrader.autonomy import AutonomousTrader


def test_universal_scan_is_cross_asset_and_stateful():
    t = AutonomousTrader()
    a = t.scan_once()
    b = t.scan_once()
    assert len(a) >= 12 and len({x["asset_class"] for x in a}) >= 8
    assert all("execution" in x and "confidence" in x for x in b)
    assert t.status()["iteration"] == 2
