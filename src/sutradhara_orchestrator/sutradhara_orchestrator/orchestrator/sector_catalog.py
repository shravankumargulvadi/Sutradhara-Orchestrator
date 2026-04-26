from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import logging
import re
import yaml

logger = logging.getLogger(__name__)


@dataclass
class SectorDefinition:
    sector_id: str
    display_name: str
    default_patrol_route: str
    assets: List[str] = field(default_factory=list)

    def to_summary(self) -> Dict[str, Any]:
        return {
            "sector_id": self.sector_id,
            "display_name": self.display_name,
            "default_patrol_route": self.default_patrol_route,
            "assets": list(self.assets),
        }


class SectorCatalog:
    def __init__(self, sectors_file: Optional[str] = None):
        self.sectors_file = sectors_file or self._default_sectors_file()
        self.sectors: List[SectorDefinition] = self._load()

    @staticmethod
    def _default_sectors_file() -> str:
        package_dir = Path(__file__).resolve().parents[2]
        workspace_src_dir = package_dir.parent
        return str(workspace_src_dir / "inspection_sim" / "config" / "sectors.yaml")

    def _load(self) -> List[SectorDefinition]:
        sectors_path = Path(self.sectors_file)
        if not sectors_path.exists():
            logger.warning("Sector catalog file %s does not exist.", sectors_path)
            return []

        try:
            data = yaml.safe_load(sectors_path.read_text()) or {}
        except Exception as exc:
            logger.error("Failed to load sector catalog from %s: %s", sectors_path, exc)
            return []

        sectors_raw = data.get("sectors", [])
        sectors: List[SectorDefinition] = []
        for item in sectors_raw:
            try:
                sectors.append(
                    SectorDefinition(
                        sector_id=item["sector_id"],
                        display_name=item.get("display_name", item["sector_id"]),
                        default_patrol_route=item["default_patrol_route"],
                        assets=list(item.get("assets", [])),
                    )
                )
            except KeyError as exc:
                logger.warning("Skipping malformed sector entry %s: missing %s", item, exc)
        return sectors

    def summaries(self) -> List[Dict[str, Any]]:
        return [sector.to_summary() for sector in self.sectors]

    def match_patrol_request(self, mission_description: str) -> Optional[SectorDefinition]:
        text = mission_description.lower()
        if not any(keyword in text for keyword in ("patrol", "sweep", "survey", "monitor")):
            return None

        explicit_sector = re.search(r"sector[\s_]?(\d+)", text)
        if explicit_sector:
            sector_id = f"sector_{explicit_sector.group(1)}"
            return next((sector for sector in self.sectors if sector.sector_id == sector_id), None)

        for sector in self.sectors:
            aliases = self._sector_aliases(sector)
            if any(alias in text for alias in aliases):
                return sector

        return None

    @staticmethod
    def _sector_aliases(sector: SectorDefinition) -> List[str]:
        aliases = {
            sector.sector_id.lower(),
            sector.display_name.lower(),
            sector.display_name.lower().replace("-", " "),
        }

        if sector.sector_id.startswith("sector_"):
            numeric = sector.sector_id.split("_", 1)[1]
            aliases.add(f"sector {numeric}")
            aliases.add(f"sector_{numeric}")

        for asset in sector.assets:
            words = asset.replace("_", " ").lower()
            aliases.add(words)
            if words.endswith(" 01"):
                aliases.add(words[:-3])

        normalized_aliases = set()
        for alias in aliases:
            normalized_aliases.add(alias.strip())
            normalized_aliases.add(alias.replace(" and ", " "))

        return sorted(a for a in normalized_aliases if a)
