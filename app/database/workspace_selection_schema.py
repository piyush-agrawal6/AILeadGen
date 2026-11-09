"""Additive personal workspace preference; membership remains authoritative."""
WORKSPACE_SELECTION_SQL = """
ALTER TABLE user_profiles ADD COLUMN active_organization_id TEXT REFERENCES organizations(id);
"""
