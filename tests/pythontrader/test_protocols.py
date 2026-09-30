from pythontrader.protocols.fix import encode_fix, parse_fix
from pythontrader.protocols.sequence import SequenceTracker


def test_fix_roundtrip():
    assert parse_fix(encode_fix([("35", "D"), ("55", "AAPL")]))["55"] == "AAPL"


def test_sequence_gap():
    s = SequenceTracker()
    assert s.accept(1)
    assert not s.accept(3)
    assert s.gaps == [(2, 2)]
