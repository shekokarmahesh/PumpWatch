import csv
import json
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from rapidfuzz.fuzz import token_set_ratio

from .models import RegistryMatch


def normalized(name: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", name.casefold()).split())


class Registry:
    def __init__(self, data_dir: Path, synthetic: bool = False):
        folder = data_dir / "registry"
        self.synthetic = synthetic
        today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        metadata = json.loads((folder / "metadata.json").read_text())
        self.ready = synthetic or bool(metadata.get("verified_complete") and metadata.get("captured_at"))
        if self.ready and not synthetic:
            age = (today - date.fromisoformat(metadata["captured_at"][:10])).days
            host = urlparse(metadata.get("source_url") or "").hostname
            self.ready = 0 <= age <= 30 and host in {"sebi.gov.in", "www.sebi.gov.in"}
        files = (
            [folder / "demo.csv"]
            if synthetic
            else [folder / "research_analysts.csv", folder / "investment_advisers.csv"]
        )
        self.rows = []
        for path in files:
            if path.exists():
                rows = list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))
                if not rows or any(not r.get("name") or not r.get("registration_number") for r in rows):
                    self.ready = False
                self.rows.extend(rows)
            else:
                self.ready = False

    def match(self, name: str, allow_not_found: bool = True) -> RegistryMatch:
        if not self.ready:
            return RegistryMatch(
                name=name,
                status="not_checked",
                note="A verified, current and complete SEBI registry has not been imported.",
            )
        prefix = "Fictional demo registry. " if self.synthetic else ""
        for row in self.rows:
            if name == row["name"] or normalized(name) == normalized(row["name"]):
                if (
                    row.get("valid_until")
                    and row["valid_until"] < datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
                ):
                    return RegistryMatch(
                        name=name,
                        status="possible",
                        similarity=1,
                        registry_row=row,
                        note=prefix + "Name matches, but recorded validity has expired; verify with SEBI.",
                    )
                return RegistryMatch(
                    name=name,
                    status="registered",
                    similarity=1,
                    registry_row=row,
                    note=prefix
                    + "Name match only; verify identity and current registration on SEBI's website.",
                )
        scores = [
            (token_set_ratio(normalized(name), normalized(row["name"])) / 100, row) for row in self.rows
        ]
        similarity, row = max(scores, key=lambda pair: pair[0]) if scores else (0, None)
        if similarity > 0.9:
            return RegistryMatch(
                name=name,
                status="possible",
                similarity=similarity,
                registry_row=row,
                note=prefix + "Similar name; identity is not confirmed.",
            )
        return RegistryMatch(
            name=name,
            status="not_found" if allow_not_found else "not_checked",
            similarity=similarity,
            note=prefix
            + (
                "No name match in the imported registry; this is not proof of unregistered activity."
                if allow_not_found
                else "Too few distinct promoters for the registry signal."
            ),
        )
