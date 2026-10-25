import pytest
from app.database.models import Business
from app.normalization.businesses import normalize_business
from app.normalization.dedupe import deduplicate_businesses, haversine_distance_meters
from app.normalization.domains import clean_website_url, normalize_domain
from app.normalization.phones import normalize_phone
from app.utils.text import calculate_name_similarity, normalize_business_name


def test_domain_normalization():
    assert normalize_domain("https://www.example.com/path?foo=bar") == "example.com"
    assert normalize_domain("http://sub.test-domain.co.uk/") == "test-domain.co.uk"
    assert normalize_domain("WWW.JOES-PIZZA.COM") == "joes-pizza.com"
    assert normalize_domain(None) is None
    assert normalize_domain("") is None


def test_phone_normalization():
    assert normalize_phone("(512) 555-0199") == "+15125550199"
    assert normalize_phone("+1 512 555 0199") == "+15125550199"
    assert normalize_phone("512-555-0199") == "+15125550199"
    assert normalize_phone("+44 20 7946 0991") == "+442079460991"
    assert normalize_phone(None) is None


def test_business_name_normalization():
    assert normalize_business_name("Joe's Pizza, Inc.") == "joes pizza"
    assert normalize_business_name("The Corner Cafe & Bakery LLC") == "the corner cafe and bakery"
    assert normalize_business_name("AUSTIN BAR & GRILL LTD") == "austin bar and grill"
    assert calculate_name_similarity("Joe's Pizza Inc", "Joes Pizza LLC") >= 90.0


def test_haversine_distance():
    # Distance between Austin Capitol and 6th Street (~800m)
    dist = haversine_distance_meters(30.2747, -97.7404, 30.2672, -97.7431)
    assert 700 < dist < 1000


def test_strong_deduplication_by_domain():
    b1 = Business(
        name="Austin Tacos",
        normalized_name="austin tacos",
        vertical="restaurant",
        website="https://www.austintacos.com",
        domain="austintacos.com",
        phone="512-555-1111",
        normalized_phone="+15125551111",
    )
    b2 = Business(
        name="Austin Tacos Downtown",
        normalized_name="austin tacos downtown",
        vertical="restaurant",
        website="https://austintacos.com/locations",
        domain="austintacos.com",
        phone="512-555-2222",
        normalized_phone="+15125552222",
    )
    unique, duplicates = deduplicate_businesses([b1, b2])
    assert len(unique) == 1
    assert len(duplicates) == 1
    assert unique[0].domain == "austintacos.com"


def test_secondary_deduplication_by_fuzzy_name_and_coords():
    b1 = Business(
        name="Little Italy Trattoria",
        normalized_name="little italy trattoria",
        vertical="restaurant",
        latitude=30.2670,
        longitude=-97.7430,
        phone="512-555-3333",
    )
    b2 = Business(
        name="Little Italy Trattoria LLC",
        normalized_name="little italy trattoria",
        vertical="restaurant",
        latitude=30.2671,
        longitude=-97.7431,  # 15 meters away
        public_email="info@littleitaly.com",
    )
    unique, duplicates = deduplicate_businesses([b1, b2])
    assert len(unique) == 1
    assert len(duplicates) == 1
    # Check merged attributes
    assert unique[0].public_email == "info@littleitaly.com"


def test_social_url_normalization():
    b = Business(
        name="Taco Truck Austin",
        normalized_name="taco truck austin",
        vertical="restaurant",
        website="https://www.instagram.com/austintacotruck/",
    )
    normalized = normalize_business(b)
    assert normalized.website is None
    assert normalized.domain is None
    assert normalized.instagram == "https://www.instagram.com/austintacotruck"


