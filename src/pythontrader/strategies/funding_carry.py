def funding_carry(funding_rate, basis_bps):
    funding = -max(-1, min(1, funding_rate * 10000 / 20))
    basis = -max(-1, min(1, basis_bps / 150))
    return 0.65 * funding + 0.35 * basis
