import re
from enum import Enum
from typing import Optional, Tuple
from app.database.models import Business


class VerticalValidationStatus(str, Enum):
    VALID = "VALID"
    UNCERTAIN = "UNCERTAIN"
    INVALID = "INVALID"


# Known non-restaurant categories and trades that must never qualify as restaurants
RESTAURANT_BLACKLIST_CATEGORIES = {
    "public_utility", "septic_service", "septic_tank_service", "legal_service",
    "barrister", "bar_association", "barber_shop", "barbershop", "barre_studio",
    "fitness_studio", "place_of_learning", "bartending_school", "school",
    "personal_or_beauty_service", "media_service", "publishing_company",
    "publisher", "supplier_or_distributor", "contractor_or_trade", "plumber",
    "roofing_contractor", "automotive_service", "car_dealer", "financial_service",
    "bank", "health_and_medical", "primary_care_or_general_clinic", "bariatric_surgeon",
    "dental_clinic", "dentist", "hospital", "veterinary_care", "lumber_yard"
}

RESTAURANT_BLACKLIST_NAME_PATTERNS = [
    r"\bseptics?\b", r"\bplumbing\b", r"\broofing\b", r"\bhvac\b", r"\belectric(al)?\b",
    r"\blaw\s+office\b", r"\battorney\b", r"\blaw\s+firm\b", r"\bdental\b", r"\bdentist\b",
    r"\bclinic\b", r"\bchiropractic\b", r"\bauto\s+repair\b", r"\bcollision\b", r"\btowing\b",
    r"\bbarber(shop)?\b", r"\bsalon\b", r"\bspa\b", r"\bvet(erinary)?\b", r"\baccounting\b",
    r"\btax\s+service\b", r"\brealt(y|or)\b", r"\bproperty\s+manage\w*\b"
]

RESTAURANT_POSITIVE_CATEGORIES = {
    "eat_and_drink", "restaurant", "cafe", "bar", "pub", "bakery", "bistro",
    "diner", "fast_food", "fast_food_restaurant", "pizza_restaurant", "pizzeria",
    "steakhouse", "food_truck", "brewery", "winery", "ice_cream", "casual_eatery",
    "sandwich_shop", "coffee_shop", "smoothie_juice_bar", "gastropub", "sports_bar",
    "wine_bar", "cocktail_bar", "snack_bar", "bar_and_grill", "seafood_restaurant",
    "bbq_restaurant", "mexican_restaurant", "italian_restaurant", "asian_restaurant",
    "sushi_restaurant", "thai_restaurant", "chinese_restaurant", "burger_restaurant"
}

RESTAURANT_POSITIVE_NAME_KEYWORDS = [
    r"\brestaurant\b", r"\bkitchen\b", r"\bgrill\b", r"\bbistro\b", r"\bcafe\b",
    r"\bcoffee\b", r"\bpizza\b", r"\bpizzeria\b", r"\btacos?\b", r"\btaqueria\b",
    r"\bbakery\b", r"\bdiner\b", r"\bbar\b", r"\bpub\b", r"\bbrewery\b", r"\beatery\b",
    r"\bb-?b-?q\b", r"\bbarbeque\b", r"\bsteakhouse\b", r"\bcantina\b", r"\bsushi\b",
    r"\bdeli\b", r"\bburgers?\b", r"\bnoodles?\b", r"\bramen\b", r"\btrattoria\b",
    r"\bosteria\b", r"\bcucina\b", r"\bwines?\b", r"\bbagels?\b", r"\bbrewhouse\b",
    r"\btaproom\b", r"\broasters?\b"
]

# Hospitality lists
HOSPITALITY_POSITIVE_CATEGORIES = {
    "accommodation", "hotel", "resort", "guest_house", "motel", "hostel",
    "bed_and_breakfast", "lodging", "inn", "boutique_hotel", "serviced_apartment",
    "extended_stay_hotel", "vacation_rental", "cabin"
}

HOSPITALITY_BLACKLIST_CATEGORIES = {
    "restaurant", "fast_food", "bar", "automotive_service", "health_and_medical",
    "legal_service", "contractor_or_trade", "retail", "supermarket"
}

# Real Estate lists
REAL_ESTATE_POSITIVE_CATEGORIES = {
    "real_estate", "real_estate_agency", "real_estate_agent", "property_management",
    "commercial_real_estate", "real_estate_consultant", "real_estate_service",
    "apartment_rental_agency"
}

REAL_ESTATE_BLACKLIST_CATEGORIES = {
    "restaurant", "hotel", "automotive_service", "health_and_medical", "plumber"
}


class VerticalValidator:
    """Deterministic, rule-based vertical validation preventing cross-niche false positives."""

    @staticmethod
    def validate(business: Business) -> Tuple[VerticalValidationStatus, str, float]:
        """
        Validate whether a candidate business belongs to its designated vertical.
        
        Returns:
            (status: VerticalValidationStatus, reason: str, confidence: float)
        """
        v_key = (business.vertical or "").lower().strip()
        subcat = (business.subcategory or "").lower().strip()
        cat = (getattr(business, "source_category", "") or "").lower().strip()
        name_lower = business.name.lower().strip()
        from app.config.verticals import get_vertical_manager
        import json
        definition = get_vertical_manager().verticals.get(v_key)
        if definition and v_key not in ("restaurant", "hospitality", "real_estate"):
            evidence = {cat, subcat}
            try:
                tags = json.loads(business.source_tags or "{}")
                if isinstance(tags, dict):
                    evidence.update(tags.get("hierarchy", []))
                    for tag in definition.osm_tags:
                        if tags.get(tag.key) in tag.values:
                            return VerticalValidationStatus.VALID, f"OSM {tag.key}={tags[tag.key]}", 0.98
            except (ValueError, TypeError):
                pass
            if evidence.intersection(definition.negative_categories):
                return VerticalValidationStatus.INVALID, "Source taxonomy belongs to another vertical", 0.98
            if evidence.intersection(definition.overture_categories) or any(subcat in tag.values for tag in definition.osm_tags):
                return VerticalValidationStatus.VALID, "Matching source taxonomy/tag evidence", 0.95
            if any(re.search(r"\b" + re.escape(signal) + r"\b", name_lower) for signal in definition.negative_name_signals):
                return VerticalValidationStatus.INVALID, "Negative trade signal without supporting taxonomy", 0.8
            return VerticalValidationStatus.UNCERTAIN, "Name signals require supporting source taxonomy", 0.5

        if v_key in ("restaurant", "restaurants", "cafe", "bar"):
            return VerticalValidator._validate_restaurant(name_lower, subcat, cat, business)
        elif v_key in ("hospitality", "hotel", "hotels", "resort"):
            return VerticalValidator._validate_hospitality(name_lower, subcat, cat, business)
        elif v_key in ("real_estate", "realtor", "property_management"):
            return VerticalValidator._validate_real_estate(name_lower, subcat, cat, business)

        # Fallback for generic or unconfigured verticals
        if subcat:
            return VerticalValidationStatus.VALID, f"Subcategory '{subcat}' present", 0.8
        return VerticalValidationStatus.UNCERTAIN, "Unconfigured vertical; requiring manual confirmation", 0.5

    @staticmethod
    def _validate_restaurant(name: str, subcat: str, cat: str, b: Business) -> Tuple[VerticalValidationStatus, str, float]:
        # 1. Check blacklisted category
        if subcat in RESTAURANT_BLACKLIST_CATEGORIES or cat in RESTAURANT_BLACKLIST_CATEGORIES:
            culprit = subcat if subcat in RESTAURANT_BLACKLIST_CATEGORIES else cat
            return (
                VerticalValidationStatus.INVALID,
                f"Source category '{culprit}' is blacklisted for restaurant vertical",
                0.0,
            )

        # 2. Check blacklisted name pattern (e.g. 'Godinez Septics', 'Austin Dental Clinic')
        for pat in RESTAURANT_BLACKLIST_NAME_PATTERNS:
            if re.search(pat, name, re.IGNORECASE):
                # Only invalidate if there is NO unequivocal restaurant category
                if subcat not in ("restaurant", "cafe", "bistro", "pizzeria"):
                    return (
                        VerticalValidationStatus.INVALID,
                        f"Business name matches non-restaurant trade pattern '{pat}'",
                        0.05,
                    )

        # 3. Check positive taxonomy evidence
        if subcat in RESTAURANT_POSITIVE_CATEGORIES or cat in ("eat_and_drink", "restaurant"):
            source_tag = "Overture" if b.source_overture else "OSM"
            return (
                VerticalValidationStatus.VALID,
                f"{source_tag} taxonomy matches restaurant domain ({subcat or cat})",
                0.95,
            )

        # 4. Check OSM tags if available
        if b.source_osm and subcat in ("restaurant", "cafe", "bar", "pub", "fast_food"):
            return (
                VerticalValidationStatus.VALID,
                f"OpenStreetMap amenity tag: {subcat}",
                0.95,
            )

        # 5. Check positive name keywords
        for kw_pat in RESTAURANT_POSITIVE_NAME_KEYWORDS:
            if re.search(kw_pat, name, re.IGNORECASE):
                return (
                    VerticalValidationStatus.VALID,
                    f"Business name indicates food/dining operation ('{name}')",
                    0.80,
                )

        # 6. If no positive or negative evidence, mark uncertain
        return (
            VerticalValidationStatus.UNCERTAIN,
            "No conclusive restaurant taxonomy or culinary indicators found",
            0.50,
        )

    @staticmethod
    def _validate_hospitality(name: str, subcat: str, cat: str, b: Business) -> Tuple[VerticalValidationStatus, str, float]:
        if subcat in HOSPITALITY_BLACKLIST_CATEGORIES or cat in HOSPITALITY_BLACKLIST_CATEGORIES:
            culprit = subcat if subcat in HOSPITALITY_BLACKLIST_CATEGORIES else cat
            return (
                VerticalValidationStatus.INVALID,
                f"Category '{culprit}' does not match hospitality vertical",
                0.0,
            )

        if subcat in HOSPITALITY_POSITIVE_CATEGORIES or cat == "accommodation":
            return (
                VerticalValidationStatus.VALID,
                f"Taxonomy indicates lodging/hospitality ({subcat or cat})",
                0.95,
            )

        if any(w in name for w in ("hotel", "resort", "inn", "motel", "suites", "lodge", "hostel", "bed & breakfast")):
            return (
                VerticalValidationStatus.VALID,
                f"Business name indicates lodging property ('{name}')",
                0.85,
            )

        return (
            VerticalValidationStatus.UNCERTAIN,
            "No definitive lodging taxonomy or hospitality keywords found",
            0.50,
        )

    @staticmethod
    def _validate_real_estate(name: str, subcat: str, cat: str, b: Business) -> Tuple[VerticalValidationStatus, str, float]:
        if subcat in REAL_ESTATE_BLACKLIST_CATEGORIES or cat in REAL_ESTATE_BLACKLIST_CATEGORIES:
            culprit = subcat if subcat in REAL_ESTATE_BLACKLIST_CATEGORIES else cat
            return (
                VerticalValidationStatus.INVALID,
                f"Category '{culprit}' does not match real estate vertical",
                0.0,
            )

        if subcat in REAL_ESTATE_POSITIVE_CATEGORIES or cat == "real_estate":
            return (
                VerticalValidationStatus.VALID,
                f"Taxonomy indicates property/real estate ({subcat or cat})",
                0.95,
            )

        if any(w in name for w in ("realty", "realtor", "real estate", "properties", "property management", "estates")):
            return (
                VerticalValidationStatus.VALID,
                f"Business name indicates real estate brokerage ('{name}')",
                0.85,
            )

        return (
            VerticalValidationStatus.UNCERTAIN,
            "No definitive property taxonomy or brokerage keywords found",
            0.50,
        )
