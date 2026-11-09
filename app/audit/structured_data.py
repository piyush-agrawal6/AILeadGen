"""Compatibility imports for preserved historical assessment consumers.

Lead Engine intake does not import or execute this parser.
"""
from app.search_visibility.structured_data import (
    VERTICAL_SCHEMA_MAP, analyze_structured_data, extract_schema_types,
)

__all__=["VERTICAL_SCHEMA_MAP","analyze_structured_data","extract_schema_types"]
