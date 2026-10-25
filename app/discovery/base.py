from abc import ABC, abstractmethod
from typing import List
from app.config.markets import MarketInfo
from app.config.verticals import VerticalDefinition
from app.database.models import Business


class BaseDiscoveryProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the discovery provider."""
        pass

    @abstractmethod
    def search(
        self,
        market: MarketInfo,
        vertical: VerticalDefinition,
        limit: int = 500,
    ) -> List[Business]:
        """Search for businesses matching market and vertical."""
        pass
