import pytest

from pythontrader.venues.binance_testnet import BinanceSpotTestnetAdapter


def test_binance_adapter_rejects_production_endpoint():
    with pytest.raises(ValueError, match="restricted"):
        BinanceSpotTestnetAdapter(base_url="https://api.binance.com")


def test_binance_adapter_requires_credentials_for_signed_requests():
    adapter = BinanceSpotTestnetAdapter()
    with pytest.raises(ValueError, match="credentials"):
        adapter.open_orders(symbol="BTCUSDT")
