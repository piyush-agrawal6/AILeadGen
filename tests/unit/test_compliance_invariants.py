"""Automated compliance regression tests (legal invariants, YouTube AI gates, privacy & terms controls)."""
from scripts.verify_compliance_invariants import verify


def test_compliance_invariants_pass():
    errors = verify()
    assert errors == [], f"Compliance invariant failures: {errors}"
