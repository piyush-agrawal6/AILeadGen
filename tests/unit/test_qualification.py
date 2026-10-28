import pytest
from app.database.models import Business
from app.config.verticals import get_vertical_manager
from app.normalization.domains import classify_social_platform, is_social_platform_domain
from app.qualification.vertical_validator import VerticalValidationStatus, VerticalValidator


def test_social_platform_classification():
    # True positives for social platforms
    assert classify_social_platform("https://www.facebook.com/mybusiness") == "facebook"
    assert classify_social_platform("http://m.facebook.com/mybusiness") == "facebook"
    assert classify_social_platform("https://instagram.com/myrestaurant") == "instagram"
    assert classify_social_platform("https://l.instagram.com/profile") == "instagram"
    assert classify_social_platform("https://linkedin.com/company/myagency") == "linkedin"
    assert classify_social_platform("https://x.com/mybar") == "x_url"
    assert classify_social_platform("https://twitter.com/mybar") == "x_url"
    assert classify_social_platform("https://tiktok.com/@myfoodtruck") == "tiktok"
    assert classify_social_platform("https://youtube.com/@myhotel") == "youtube"
    assert classify_social_platform("https://threads.net/@mycafe") == "threads"
    assert is_social_platform_domain("https://pinterest.com/myrealtor") is True

    # Legitimate hosted platforms must NOT be classified as social
    assert classify_social_platform("https://buda-biscuit.square.site") is None
    assert classify_social_platform("https://myrestaurant.wixsite.com/home") is None
    assert classify_social_platform("https://myhotel.wordpress.com") is None
    assert classify_social_platform("https://realestate.webflow.io") is None
    assert classify_social_platform("https://customdomain.squarespace.com") is None
    assert is_social_platform_domain("https://buda-biscuit.square.site") is False


def test_vertical_validator_rejection_of_false_positives():
    # 1. Godinez Septics with 'public_utility' should be rejected as INVALID
    b_septic = Business(
        name="Godinez Septics",
        normalized_name="godinez septics",
        vertical="restaurant",
        subcategory="public_utility",
        source_category="public_utility",
        source_overture=True,
    )
    status, reason, conf = VerticalValidator.validate(b_septic)
    assert status == VerticalValidationStatus.INVALID
    assert "public_utility" in reason or "septic" in reason.lower()

    # 2. Austin Dental Clinic should be rejected as INVALID
    b_dental = Business(
        name="Austin Dental Clinic",
        normalized_name="austin dental clinic",
        vertical="restaurant",
        subcategory="health_and_medical",
    )
    status, reason, conf = VerticalValidator.validate(b_dental)
    assert status == VerticalValidationStatus.INVALID

    # 3. Barber shop matching 'bar' should be rejected as INVALID
    b_barber = Business(
        name="Downtown Barber Shop",
        normalized_name="downtown barber shop",
        vertical="restaurant",
        subcategory="barber_shop",
    )
    status, reason, conf = VerticalValidator.validate(b_barber)
    assert status == VerticalValidationStatus.INVALID


def test_vertical_validator_acceptance_of_legitimate_businesses():
    # 1. Valid restaurant taxonomy
    b_rest = Business(
        name="Bella Roma Italian Kitchen",
        normalized_name="bella roma italian kitchen",
        vertical="restaurant",
        subcategory="restaurant",
        source_overture=True,
    )
    status, reason, conf = VerticalValidator.validate(b_rest)
    assert status == VerticalValidationStatus.VALID
    assert conf >= 0.8

    # 2. Valid cafe by name keywords even if category is generic
    b_cafe = Business(
        name="South Congress Coffee & Bakery",
        normalized_name="south congress coffee and bakery",
        vertical="restaurant",
        subcategory="commercial_services",
    )
    status, reason, conf = VerticalValidator.validate(b_cafe)
    assert status == VerticalValidationStatus.VALID

    # 3. Valid hotel
    b_hotel = Business(
        name="The Driskill Hotel",
        normalized_name="the driskill hotel",
        vertical="hospitality",
        subcategory="hotel",
    )
    status, reason, conf = VerticalValidator.validate(b_hotel)
    assert status == VerticalValidationStatus.VALID


def test_chain_detection_and_reasons():
    vm = get_vertical_manager()

    # National fast-food chain by name
    is_chain, reason, conf = vm.check_chain(name="Chipotle Mexican Grill", domain="chipotle.com", vertical_key="restaurant")
    assert is_chain is True
    assert "chipotle" in reason.lower()
    assert conf >= 0.9

    # National hotel chain by domain
    is_chain, reason, conf = vm.check_chain(name="Austin Downtown Marriott", domain="marriott.com", vertical_key="hospitality")
    assert is_chain is True
    assert "marriott.com" in reason

    # Local group with high frequency
    is_chain, reason, conf = vm.check_chain(name="Local Group", domain="localgroup.com", domain_frequency=6)
    assert is_chain is True
    assert "frequency" in reason.lower()

    # Independent business
    is_chain, reason, conf = vm.check_chain(name="Joe's Neighborhood Pizza", domain="joespizzatx.com", domain_frequency=1)
    assert is_chain is False
    assert reason is None
