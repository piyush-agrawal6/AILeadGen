import json
import logging
import re
from typing import List, Set, Tuple
from bs4 import BeautifulSoup

logger = logging.getLogger("leadengine.audit.structured_data")

VERTICAL_SCHEMA_MAP = {
    "restaurant": {"restaurant", "foodestablishment", "cafeorcoffeeshop", "barorpub", "winery", "fastfoodrestaurant"},
    "hospitality": {"hotel", "lodgingbusiness", "motel", "hostel", "resort", "bedandbreakfast"},
    "real_estate": {"realestateagent", "realestateagency", "realestatelisting"},
}


def extract_schema_types(obj: any, collected: Set[str]) -> None:
    """Recursively collect @type strings from parsed JSON-LD object."""
    if isinstance(obj, dict):
        t = obj.get("@type")
        if isinstance(t, str):
            collected.add(t)
        elif isinstance(t, list):
            for item in t:
                if isinstance(item, str):
                    collected.add(item)
        for v in obj.values():
            extract_schema_types(v, collected)
    elif isinstance(obj, list):
        for item in obj:
            extract_schema_types(item, collected)


def analyze_structured_data(html: str, vertical_key: str = "restaurant") -> Tuple[bool, List[str], bool]:
    """Parse JSON-LD structured data and detect schema types and vertical compatibility.
    
    Returns:
        (schema_present, schema_types_list, vertical_schema_present)
    """
    if not html:
        return False, [], False

    soup = BeautifulSoup(html, "lxml")
    ld_scripts = soup.find_all("script", type="application/ld+json")
    if not ld_scripts:
        return False, [], False

    schema_types: Set[str] = set()

    for script in ld_scripts:
        content = script.string
        if not content:
            continue
        try:
            # Clean common syntax errors (e.g. comments, trailing commas)
            cleaned = content.strip()
            data = json.loads(cleaned)
            extract_schema_types(data, schema_types)
        except Exception:
            # Try regex fallback for "@type": "..."
            matches = re.findall(r'["\']@type["\']\s*:\s*["\']([a-zA-Z0-9_]+)["\']', content)
            for m in matches:
                schema_types.add(m)

    types_list = sorted(list(schema_types))
    schema_present = len(types_list) > 0

    # Check if vertical specific schema is present
    expected_types = VERTICAL_SCHEMA_MAP.get(vertical_key.lower(), set())
    norm_types = {t.lower() for t in schema_types}
    vertical_schema_present = bool(norm_types & expected_types)

    return schema_present, types_list, vertical_schema_present
