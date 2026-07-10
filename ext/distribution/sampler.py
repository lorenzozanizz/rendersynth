from typing import List
from abc import ABCMeta, abstractmethod

class CompiledSampler(metaclass=ABCMeta):
    """Base sampler interface"""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return dimensionality of samples"""
        pass

    @abstractmethod
    def sample(self) -> List[float]:
        """Sample a vector of shape (dimension,)"""
        pass
