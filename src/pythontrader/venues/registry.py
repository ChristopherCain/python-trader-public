class VenueRegistry:
    def __init__(self):
        self._venues = {}

    def register(self, venue):
        self._venues[venue.capabilities.name] = venue

    def get(self, name):
        return self._venues[name]

    def health(self):
        return {n: v.health() for n, v in self._venues.items()}

    def capabilities(self):
        return {n: v.capabilities for n, v in self._venues.items()}
