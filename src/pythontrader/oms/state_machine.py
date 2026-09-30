from enum import Enum


class State(str, Enum):
    CREATED = "created"
    ROUTED = "routed"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


ALLOWED = {
    State.CREATED: {State.ROUTED, State.CANCELED, State.REJECTED},
    State.ROUTED: {State.PARTIAL, State.FILLED, State.CANCELED, State.REJECTED},
    State.PARTIAL: {State.PARTIAL, State.FILLED, State.CANCELED},
}


class OrderStateMachine:
    def __init__(self):
        self.state = State.CREATED

    def transition(self, to: State):
        if to not in ALLOWED.get(self.state, set()):
            raise ValueError(f"invalid transition {self.state}->{to}")
        self.state = to
