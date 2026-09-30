from pythontrader.security.redaction import redact
from pythontrader.security.signing import sign, verify


def test_signing():
    s = sign(b"k", b"x")
    assert verify(b"k", b"x", s) and not verify(b"z", b"x", s)


def test_redaction():
    assert redact({"api_key": "x", "user": "a"}) == {"api_key": "***", "user": "a"}
