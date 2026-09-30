def turnover(fills, average_equity):
    return sum(abs(f.qty * f.price) for f in fills) / average_equity if average_equity else 0.0
