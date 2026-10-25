import math
from typing import Dict, List, Set, Tuple
from app.database.models import Business
from app.utils.text import calculate_name_similarity


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute distance in meters between two lat/lon pairs."""
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def merge_businesses(primary: Business, secondary: Business) -> Business:
    """Merge details from secondary into primary, preserving primary identity."""
    if secondary.source_overture:
        primary.source_overture = True
    if secondary.source_osm:
        primary.source_osm = True

    # Blend confidence
    primary.source_confidence = max(primary.source_confidence, secondary.source_confidence)

    # Merge contact details if missing
    if not primary.website and secondary.website:
        primary.website = secondary.website
        primary.domain = secondary.domain
    elif not primary.domain and secondary.domain:
        primary.domain = secondary.domain

    if not primary.phone and secondary.phone:
        primary.phone = secondary.phone
        primary.normalized_phone = secondary.normalized_phone

    if not primary.public_email and secondary.public_email:
        primary.public_email = secondary.public_email

    if not primary.instagram and secondary.instagram:
        primary.instagram = secondary.instagram
    if not primary.facebook and secondary.facebook:
        primary.facebook = secondary.facebook
    if not primary.linkedin and secondary.linkedin:
        primary.linkedin = secondary.linkedin
    if not primary.x_url and secondary.x_url:
        primary.x_url = secondary.x_url

    if not primary.address and secondary.address:
        primary.address = secondary.address
    if not primary.postcode and secondary.postcode:
        primary.postcode = secondary.postcode

    if primary.latitude is None and secondary.latitude is not None:
        primary.latitude = secondary.latitude
        primary.longitude = secondary.longitude

    if secondary.external_overture_id and not primary.external_overture_id:
        primary.external_overture_id = secondary.external_overture_id
    if secondary.external_osm_id and not primary.external_osm_id:
        primary.external_osm_id = secondary.external_osm_id

    return primary


def deduplicate_businesses(businesses: List[Business]) -> Tuple[List[Business], List[Business]]:
    """Deduplicate a list of businesses.
    
    Returns:
        (unique_businesses, duplicate_businesses)
    """
    domain_map: Dict[str, int] = {}
    phone_map: Dict[str, int] = {}
    unique: List[Business] = []
    duplicates: List[Business] = []

    for b in businesses:
        is_dup = False
        target_idx: Optional[int] = None

        # 1. Strong duplicate: Same normalized domain
        if b.domain:
            if b.domain in domain_map:
                is_dup = True
                target_idx = domain_map[b.domain]

        # 2. Strong duplicate: Same normalized phone
        if not is_dup and b.normalized_phone:
            if b.normalized_phone in phone_map:
                is_dup = True
                target_idx = phone_map[b.normalized_phone]

        # 3. Secondary duplicate: Fuzzy name match + nearby coordinates / matching address
        if not is_dup and b.normalized_name:
            for idx, existing in enumerate(unique):
                sim = calculate_name_similarity(b.name, existing.name)
                if sim >= 85.0:
                    # Check distance if both have coordinates
                    if (
                        b.latitude is not None and b.longitude is not None
                        and existing.latitude is not None and existing.longitude is not None
                    ):
                        dist = haversine_distance_meters(
                            b.latitude, b.longitude, existing.latitude, existing.longitude
                        )
                        if dist <= 300.0:  # Within 300 meters
                            is_dup = True
                            target_idx = idx
                            break
                    # Or matching address
                    elif (
                        b.address and existing.address
                        and b.address.lower() == existing.address.lower()
                    ):
                        is_dup = True
                        target_idx = idx
                        break

        if is_dup and target_idx is not None:
            # Merge into existing unique business
            unique[target_idx] = merge_businesses(unique[target_idx], b)
            b.is_duplicate = True
            duplicates.append(b)
        else:
            idx = len(unique)
            unique.append(b)
            if b.domain:
                domain_map[b.domain] = idx
            if b.normalized_phone:
                phone_map[b.normalized_phone] = idx

    return unique, duplicates
