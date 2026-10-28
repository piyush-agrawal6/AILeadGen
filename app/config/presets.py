import json
from pathlib import Path

CONFIG_ROOT = Path(__file__).resolve().parents[2] / "config"


def market_presets():
    return json.loads((CONFIG_ROOT / "market_presets.json").read_text(encoding="utf8"))


def quality_modes():
    return json.loads((CONFIG_ROOT / "lead_quality.json").read_text(encoding="utf8"))
