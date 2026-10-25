from pathlib import Path
from typing import Dict, List, Optional, Set
import yaml
from pydantic import BaseModel, Field


class OSMTag(BaseModel):
    key: str
    values: List[str]


class VerticalDefinition(BaseModel):
    key: str
    display_name: str
    aliases: List[str] = Field(default_factory=list)
    overture_categories: List[str] = Field(default_factory=list)
    osm_tags: List[OSMTag] = Field(default_factory=list)
    exclude_keywords: List[str] = Field(default_factory=list)


class VerticalManager:
    def __init__(
        self,
        verticals_path: str = "config/verticals.yaml",
        chains_path: str = "config/chain_domains.yaml",
    ):
        self.verticals_path = Path(verticals_path)
        self.chains_path = Path(chains_path)
        self.verticals: Dict[str, VerticalDefinition] = {}
        self.alias_map: Dict[str, str] = {}
        self.chain_domains: Set[str] = set()
        self.max_domain_occurrences: int = 4
        self._load()

    def _load(self) -> None:
        if self.verticals_path.exists():
            with open(self.verticals_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
                for key, val in raw.items():
                    v_def = VerticalDefinition(
                        key=key,
                        display_name=val.get("display_name", key.title()),
                        aliases=val.get("aliases", []),
                        overture_categories=val.get("overture_categories", []),
                        osm_tags=[OSMTag(**t) for t in val.get("osm_tags", [])],
                        exclude_keywords=[kw.lower() for kw in val.get("exclude_keywords", [])],
                    )
                    self.verticals[key] = v_def
                    self.alias_map[key.lower()] = key
                    for alias in v_def.aliases:
                        self.alias_map[alias.lower()] = key

        if self.chains_path.exists():
            with open(self.chains_path, "r", encoding="utf-8") as f:
                c_raw = yaml.safe_load(f) or {}
                self.chain_domains = {d.lower().strip() for d in c_raw.get("domains", [])}
                thresholds = c_raw.get("thresholds", {})
                self.max_domain_occurrences = thresholds.get("max_domain_occurrences", 4)

    def resolve_vertical(self, name_or_alias: str) -> Optional[VerticalDefinition]:
        """Resolve a vertical key from alias, key, or category string."""
        if not name_or_alias:
            return None
        cleaned = name_or_alias.strip().lower()
        key = self.alias_map.get(cleaned)
        if key:
            return self.verticals.get(key)
        # Partial match if needed
        for alias, v_key in self.alias_map.items():
            if alias in cleaned or cleaned in alias:
                return self.verticals.get(v_key)
        return None

    def list_verticals(self) -> List[VerticalDefinition]:
        """List all configured verticals."""
        return list(self.verticals.values())

    def is_chain_name(self, name: str, vertical_key: Optional[str] = None) -> bool:
        """Check if business name matches known franchise/chain keywords."""
        if not name:
            return False
        clean_name = name.lower()
        # Check specific vertical keywords
        if vertical_key and vertical_key in self.verticals:
            for kw in self.verticals[vertical_key].exclude_keywords:
                if kw in clean_name:
                    return True
        # Check across all verticals
        for v in self.verticals.values():
            for kw in v.exclude_keywords:
                if kw in clean_name:
                    return True
        return False

    def is_chain_domain(self, domain: str) -> bool:
        """Check if domain is in the known chain domains list."""
        if not domain:
            return False
        clean_d = domain.lower().strip()
        # Direct match or subdomain of chain domain
        if clean_d in self.chain_domains:
            return True
        for cd in self.chain_domains:
            if clean_d.endswith("." + cd):
                return True
        return False


_vertical_manager_instance: Optional[VerticalManager] = None


def get_vertical_manager() -> VerticalManager:
    global _vertical_manager_instance
    if _vertical_manager_instance is None:
        _vertical_manager_instance = VerticalManager()
    return _vertical_manager_instance
