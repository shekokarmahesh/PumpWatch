import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
ROOT = Path(__file__).resolve().parents[3]
DISCLAIMER = "This tool measures public attention, not value. It is not investment advice."
Mode = Literal["live", "cache-first", "replay"]


@dataclass
class Settings:
    mode: Mode = field(default_factory=lambda: os.getenv("PUMPWATCH_MODE", "replay"))
    api_key: str = field(default_factory=lambda: os.getenv("SERPAPI_KEY", ""), repr=False)
    state_dir: Path = field(
        default_factory=lambda: Path(os.getenv("PUMPWATCH_STATE_DIR", str(ROOT / ".local")))
    )
    data_dir: Path = DATA_DIR
    monthly_budget: int = field(default_factory=lambda: int(os.getenv("PUMPWATCH_MONTHLY_BUDGET", "250")))
    hourly_budget: int = field(default_factory=lambda: int(os.getenv("PUMPWATCH_HOURLY_BUDGET", "250")))

    def __post_init__(self):
        if self.mode not in {"live", "cache-first", "replay"}:
            raise ValueError("PUMPWATCH_MODE must be live, cache-first or replay")
        self.state_dir = self.state_dir.resolve()
