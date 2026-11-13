# Intent Radar subscriptions — verification in progress

This is a current checkpoint, not a declaration of completion. See
PAYMENT_TEST_RESULTS.md for actual fixtures versus real provider acceptance,
INTENT_RADAR_LAUNCH_REPORT.md for deployed commits, RAZORPAY_INTEGRATION.md for the
provider contract, and SUBSCRIPTION_ARCHITECTURE.md for additive schema and rollback.

Razorpay Test Mode credentials are present but the real API returned HTTP 401,
including after the owner supplied a corrected pair. Internal plan creation and
real checkout/lifecycle acceptance are blocked. No real charges or public paid
checkout are enabled. Existing authorized owner beta access remains available.
