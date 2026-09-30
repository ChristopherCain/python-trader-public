SOH = "\x01"


def parse_fix(raw: str) -> dict[str, str]:
    sep = SOH if SOH in raw else "|"
    out = {}
    for part in raw.strip(sep).split(sep):
        if not part:
            continue
        if "=" not in part:
            raise ValueError("malformed FIX field")
        k, v = part.split("=", 1)
        out[k] = v
    return out


def encode_fix(fields: list[tuple[str, str]], separator: str = SOH) -> str:
    return separator.join(f"{k}={v}" for k, v in fields) + separator
