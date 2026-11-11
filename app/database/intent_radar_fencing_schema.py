"""Capture monitor revisions without changing existing signal or Lead Engine data."""
INTENT_RADAR_FENCING_SQL = """
ALTER TABLE intent_discoveries ADD COLUMN monitor_revision INTEGER;
"""
