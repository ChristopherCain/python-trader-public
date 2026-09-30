SENSITIVE = {"authorization", "api_key", "secret", "token", "password"}


def redact(mapping: dict) -> dict:
    out = {}
    for k, v in mapping.items():
        out[k] = "***" if k.lower() in SENSITIVE else v
    return out
