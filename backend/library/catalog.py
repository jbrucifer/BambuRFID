"""
Tag Library — indexes and serves genuine Bambu Lab RFID tag dumps from
the community-maintained Bambu-Lab-RFID-Library repository.

Repository: https://github.com/queengooborg/Bambu-Lab-RFID-Library
Structure:  Material/SubType/Color/UID/hf-mf-{UID}-dump.json

Each JSON dump contains hex-encoded block data for all 64 MIFARE Classic blocks,
including the RSA-2048 signature — making them valid for cloning to Magic/FUID tags.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import aiofiles
import httpx

logger = logging.getLogger(__name__)

REPO_OWNER = "queengooborg"
REPO_NAME = "Bambu-Lab-RFID-Library"
GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"

# Local cache directory
CACHE_DIR = Path(__file__).resolve().parent.parent / "library_cache"


@dataclass
class TagEntry:
    """A single tag dump entry in the catalog."""
    material: str          # e.g. "PLA"
    subtype: str           # e.g. "PLA Matte"
    color: str             # e.g. "Charcoal"
    uid: str               # e.g. "7AD43F1C"
    json_path: str         # Full path in repo
    bin_path: str = ""     # .bin path if available

    @property
    def display_name(self) -> str:
        return f"{self.subtype} - {self.color}"

    @property
    def id(self) -> str:
        return f"{self.material}/{self.subtype}/{self.color}/{self.uid}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "material": self.material,
            "subtype": self.subtype,
            "color": self.color,
            "uid": self.uid,
            "display_name": self.display_name,
            "json_path": self.json_path,
        }


@dataclass
class TagCatalog:
    """Full catalog of available tag dumps."""
    entries: list[TagEntry] = field(default_factory=list)
    materials: dict[str, list[str]] = field(default_factory=dict)  # material -> [subtypes]
    last_updated: str = ""

    def to_dict(self) -> dict:
        return {
            "total": len(self.entries),
            "materials": self.materials,
            "last_updated": self.last_updated,
        }


class TagLibrary:
    """Manages the tag dump library — indexing, searching, and downloading."""

    def __init__(self):
        self.catalog = TagCatalog()
        self._index_loaded = False
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def is_loaded(self) -> bool:
        return self._index_loaded

    async def load_index(self, force_refresh: bool = False):
        """
        Load the catalog index from GitHub (or local cache).
        Uses the GitHub Trees API to list all files without downloading them.
        """
        cache_file = CACHE_DIR / "catalog.json"

        # Try cache first
        if not force_refresh and cache_file.exists():
            try:
                async with aiofiles.open(str(cache_file), "r") as f:
                    data = json.loads(await f.read())
                self._rebuild_from_cache(data)
                logger.info(f"Loaded {len(self.catalog.entries)} entries from cache")
                return
            except Exception as e:
                logger.warning(f"Cache load failed: {e}")

        # Fetch from GitHub
        url = f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/main?recursive=1"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=30)
            resp.raise_for_status()
            tree = resp.json()

        entries = []
        for item in tree.get("tree", []):
            path = item["path"]
            if not path.endswith("-dump.json"):
                continue
            parts = path.split("/")
            if len(parts) < 4:
                continue
            material = parts[0]
            subtype = parts[1]
            color = parts[2]
            uid = parts[3]
            entries.append(TagEntry(
                material=material,
                subtype=subtype,
                color=color,
                uid=uid,
                json_path=path,
            ))

        self.catalog.entries = entries
        self._build_material_index()
        self._index_loaded = True

        # Save to cache
        cache_data = [e.to_dict() for e in entries]
        async with aiofiles.open(str(cache_file), "w") as f:
            await f.write(json.dumps(cache_data))

        logger.info(f"Indexed {len(entries)} tag dumps from GitHub")

    def _rebuild_from_cache(self, data: list[dict]):
        """Rebuild catalog from cached JSON."""
        self.catalog.entries = [
            TagEntry(
                material=d["material"],
                subtype=d["subtype"],
                color=d["color"],
                uid=d["uid"],
                json_path=d["json_path"],
            )
            for d in data
        ]
        self._build_material_index()
        self._index_loaded = True

    def _build_material_index(self):
        """Build the material -> subtypes lookup."""
        materials: dict[str, set[str]] = {}
        for e in self.catalog.entries:
            if e.material not in materials:
                materials[e.material] = set()
            materials[e.material].add(e.subtype)
        self.catalog.materials = {k: sorted(v) for k, v in sorted(materials.items())}

    def search(self, material: Optional[str] = None, subtype: Optional[str] = None,
               color: Optional[str] = None, query: Optional[str] = None) -> list[TagEntry]:
        """Search the catalog with optional filters."""
        results = self.catalog.entries

        if material:
            results = [e for e in results if e.material.lower() == material.lower()]
        if subtype:
            results = [e for e in results if e.subtype.lower() == subtype.lower()]
        if color:
            color_lower = color.lower()
            results = [e for e in results if color_lower in e.color.lower()]
        if query:
            q = query.lower()
            results = [e for e in results
                       if q in e.material.lower()
                       or q in e.subtype.lower()
                       or q in e.color.lower()
                       or q in e.uid.lower()]

        return results

    def get_colors(self, material: str, subtype: str) -> list[str]:
        """Get available colors for a material/subtype combination."""
        colors = set()
        for e in self.catalog.entries:
            if e.material == material and e.subtype == subtype:
                colors.add(e.color)
        return sorted(colors)

    async def download_dump(self, entry: TagEntry) -> dict:
        """
        Download a specific tag dump JSON from GitHub.
        Returns the parsed JSON with block data.
        """
        # Check local cache first
        cache_path = CACHE_DIR / entry.uid / f"{entry.uid}-dump.json"
        if cache_path.exists():
            async with aiofiles.open(str(cache_path), "r") as f:
                return json.loads(await f.read())

        # Download from GitHub
        url = f"{GITHUB_RAW}/{REPO_OWNER}/{REPO_NAME}/main/{entry.json_path}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

        # Cache locally
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(str(cache_path), "w") as f:
            await f.write(json.dumps(data))

        return data

    def dump_to_blocks(self, dump_data: dict) -> list[bytes]:
        """Convert a JSON dump's block data to a list of 64 × 16-byte blocks."""
        blocks_dict = dump_data.get("blocks", {})
        blocks = []
        for i in range(64):
            hex_str = blocks_dict.get(str(i), "00" * 16)
            blocks.append(bytes.fromhex(hex_str))
        return blocks


# Global singleton
tag_library = TagLibrary()
