from abc import ABC, abstractmethod

from pythontrader.domain import Signal
from pythontrader.features.engine import FeatureVector


class Strategy(ABC):
    name = "base"

    @abstractmethod
    def evaluate(self, f: FeatureVector) -> Signal:
        raise NotImplementedError
