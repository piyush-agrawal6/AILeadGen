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
        raw_budget = min(settings.max_raw_businesses, getattr(self, "raw_limit", None) or settings.max_raw_businesses)
        raw_target = min(max(target_leads * multiplier, 100), max(1, raw_budget // 2))

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
        raw_businesses = raw_businesses[:raw_budget]

        logger.info(f"Total raw businesses discovered: {len(raw_businesses)}")

        # 4. Deduplicate
        unique_businesses, duplicates = deduplicate_businesses(raw_businesses)
        for d in duplicates:
            d.is_duplicate = True
            d.is_rejected = True
            d.rejection_reason = "DUPLICATE"
            d.processing_status = ProcessingStatus.REJECTED.value

        logger.info(f"After deduplication: {len(unique_businesses)} unique, {len(duplicates)} duplicates.")

        # 5. Chain and Relevance Filtering
        from app.qualification.vertical_validator import VerticalValidationStatus, VerticalValidator

        domain_counts = Counter(b.domain for b in unique_businesses if b.domain)

        candidates: List[Business] = []
        rejected: List[Business] = list(duplicates)

        for b in unique_businesses:
            b.processing_status = ProcessingStatus.NORMALIZED.value

            # Check if name is blank or invalid
            if not b.name or len(b.name.strip()) < 2:
                b.is_rejected = True
                b.rejection_reason = "INVALID_NAME"
                b.processing_status = ProcessingStatus.REJECTED.value
                rejected.append(b)
                continue

            # Check vertical validation
            val_status, val_reason, val_conf = VerticalValidator.validate(b)
            b.vertical_validation_status = val_status.value
            b.vertical_validation_reason = val_reason
            b.vertical_validation_confidence = val_conf

            if val_status == VerticalValidationStatus.INVALID:
                b.is_rejected = True
                b.rejection_reason = "VERTICAL_MISMATCH"
                b.processing_status = ProcessingStatus.REJECTED.value
                rejected.append(b)
                continue
            elif val_status == VerticalValidationStatus.UNCERTAIN:
                b.is_rejected = True
                b.rejection_reason = "UNCERTAIN_NICHE"
                b.processing_status = ProcessingStatus.REJECTED.value
                rejected.append(b)
                continue

            # Check chain / franchise status
            freq = domain_counts.get(b.domain, 1) if b.domain else 1
            is_chain, chain_reason, chain_conf = self.vertical_mgr.check_chain(
                name=b.name,
                domain=b.domain,
                vertical_key=vertical.key,
                domain_frequency=freq,
            )
            b.is_chain = is_chain
            if getattr(self,"phase3_scale",False) and chain_reason and chain_reason.startswith("High domain frequency"):
                is_chain = False
                b.is_chain = False
                chain_reason = "Repeated domain observed; scale requires corroborating location/city evidence"
                chain_conf = 0.5
            b.chain_reason = chain_reason
            b.chain_confidence = chain_conf

            if is_chain and not include_chains:
                b.is_rejected = True
                b.rejection_reason = "CHAIN"
                b.processing_status = ProcessingStatus.REJECTED.value
                rejected.append(b)
                continue

            candidates.append(b)

        logger.info(f"After chain & quality filtering: {len(candidates)} candidates remain.")
        return market, vertical, candidates, rejected
