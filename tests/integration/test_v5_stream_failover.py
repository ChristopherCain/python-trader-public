from pythontrader.execution.kill_switch import ExecutionKillSwitch
from pythontrader.execution.venue_failover import VenueFailoverManager
from pythontrader.venues.websocket_runtime import StreamState, WebSocketSupervisor


def test_stale_stream_can_trip_execution_gate_and_failover_venue():
    stream = WebSocketSupervisor(stale_after_s=2)
    switch = ExecutionKillSwitch(max_stale_feed_ms=2_000)
    failover = VenueFailoverManager(failure_threshold=1, cooldown_s=5)

    stream.connected(now=10)
    assert stream.heartbeat(now=11)
    assert not stream.heartbeat(now=12)
    assert stream.state is StreamState.BACKOFF

    switch.record_feed_staleness(2_000)
    failover.record_failure("alpha", now=12)

    assert not switch.allow_execution()
    assert not failover.eligible("alpha", now=13)
    assert failover.eligible("beta", now=13)
