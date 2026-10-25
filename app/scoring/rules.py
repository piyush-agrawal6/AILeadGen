from pathlib import Path
from typing import Any, Dict
import yaml


class ScoringConfig:
    def __init__(self, config_path: str = "config/scoring.yaml"):
        self.config_path = Path(config_path)
        self.weights: Dict[str, Any] = {}
        self.caps: Dict[str, float] = {
            "website_max": 55.0,
            "seo_max": 20.0,
            "vertical_max": 15.0,
            "contactability_max": 10.0,
        }
        self.tiers: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self.weights = data.get("weights", {})
                self.caps = data.get("caps", self.caps)
                self.tiers = data.get("tiers", {})

    def get_tier(self, score: float) -> str:
        """Assign letter tier based on 0-100 score."""
        if score >= 80.0:
            return "A+"
        elif score >= 65.0:
            return "A"
        elif score >= 50.0:
            return "B"
        elif score >= 35.0:
            return "C"
        else:
            return "D"


_scoring_config_instance: ScoringConfig = None


def get_scoring_config() -> ScoringConfig:
    global _scoring_config_instance
    if _scoring_config_instance is None:
        _scoring_config_instance = ScoringConfig()
    return _scoring_config_instance
