import logging
from collections import Counter
from typing import Dict, List, Optional, Tuple

from app.config.markets import MarketInfo, resolve_market
from app.config.settings import get_settings
from app.config.verticals import VerticalDefinition, get_vertical_manager
from app.database.models import Business, ProcessingStatus
from app.discovery.osm import OSMDiscoveryProvider
from app.discovery.overture import OvertureDiscoveryProvider
from app.normalization.dedupe import deduplicate_businesses

logger = logging.getLogger("leadengine.discovery.resolver")


class DiscoveryCoordinator:
    def __init__(self):
        self.overture_provider = OvertureDiscoveryProvider()
        self.osm_provider = OSMDiscoveryProvider()
        self.vertical_mgr = get_vertical_manager()

    def discover(
        self,
        market_str: str,
        vertical_str: str,
        target_leads: int = 250,
        include_chains: bool = False,
    ) -> Tuple[MarketInfo, VerticalDefinition, List[Business], List[Business]]:
        """Discover and deduplicate businesses for a market and vertical.
        
        Returns:
            (market_info, vertical_def, candidates, rejected_or_duplicates)
        """
        settings = get_settings()
        multiplier = settings.discovery.raw_multiplier or 10
        raw_target = max(target_leads * multiplier, 500)

        # 1. Resolve market
        market = resolve_market(market_str)
        logger.info(f"Resolved market: {market.city}, {market.state}, {market.country} (bbox: {market.bbox.to_tuple()})")

        # 2. Resolve vertical
        vertical = self.vertical_mgr.resolve_vertical(vertical_str)
        if not vertical:
            raise ValueError(f"Unknown vertical '{vertical_str}'. Check config/verticals.yaml for supported verticals.")

        # 3. Query discovery providers
        raw_businesses: List[Business] = []

        # Query Overture
        overture_businesses = self.overture_provider.search(market, vertical, limit=raw_target)
        raw_businesses.extend(overture_businesses)

        # Query OSM
        osm_businesses = self.osm_provider.search(market, vertical, limit=raw_target)
        raw_businesses.extend(osm_businesses)

        logger.info(f"Total raw businesses discovered: {len(raw_businesses)}")

        # 4. Deduplicate
        unique_businesses, duplicates = deduplicate_businesses(raw_businesses)
        logger.info(f"After deduplication: {len(unique_businesses)} unique, {len(duplicates)} duplicates.")

        # 5. Chain and Relevance Filtering
        # Count domain frequencies to catch regional/national multi-location groups
        domain_counts = Counter(b.domain for b in unique_businesses if b.domain)

        candidates: List[Business] = []
        rejected: List[Business] = list(duplicates)

        for b in unique_businesses:
            b.processing_status = ProcessingStatus.NORMALIZED.value

            # Check if domain appears too many times in this scan
            is_frequency_chain = False
            if b.domain and domain_counts[b.domain] > self.vertical_mgr.max_domain_occurrences:
                is_frequency_chain = True

            # Check known chain domains
            is_domain_chain = bool(b.domain and self.vertical_mgr.is_chain_domain(b.domain))

            # Check known chain names
            is_name_chain = self.vertical_mgr.is_chain_name(b.name, vertical.key)

            if is_frequency_chain or is_domain_chain or is_name_chain:
                b.is_chain = True
                if not include_chains:
                    b.is_rejected = True
                    b.rejection_reason = "CHAIN_OR_FRANCHISE"
                    b.processing_status = ProcessingStatus.REJECTED.value
                    rejected.append(b)
                    continue

            # Check if name is blank or invalid
            if not b.name or len(b.name.strip()) < 2:
                b.is_rejected = True
                b.rejection_reason = "INVALID_NAME"
                b.processing_status = ProcessingStatus.REJECTED.value
                rejected.append(b)
                continue

            candidates.append(b)

        logger.info(f"After chain & quality filtering: {len(candidates)} candidates remain.")
        return market, vertical, candidates, rejected
