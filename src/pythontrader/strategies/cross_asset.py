def relative_value(a_return, b_return, beta=1.0):
    spread = a_return - beta * b_return
    return max(-1.0, min(1.0, -spread * 25))
