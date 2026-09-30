class SequenceTracker:
    def __init__(self, start: int = 1):
        self.expected = start
        self.gaps = []

    def accept(self, seq: int) -> bool:
        if seq == self.expected:
            self.expected += 1
            return True
        if seq > self.expected:
            self.gaps.append((self.expected, seq - 1))
            self.expected = seq + 1
            return False
        return False
