from uuid import uuid4


def order_id(prefix="ord"):
    return f"{prefix}_{uuid4().hex[:20]}"
