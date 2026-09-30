from pythontrader.replay import DeterministicReplay

if __name__ == "__main__":
    stats = DeterministicReplay(seed=7).run(250_000)
    print(f"events={stats.events:,}")
    print(f"decisions={stats.decisions:,}")
    print(f"orders={stats.orders:,}")
    print(f"fills={stats.fills:,}")
    print(f"rejects={stats.rejects:,}")
    print(f"elapsed={stats.elapsed_s:.3f}s")
    print(f"throughput={stats.events_per_second:,.0f} events/s")
    print(f"checksum={stats.checksum:016x}")
