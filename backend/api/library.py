"""API routes for the community tag dump library."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.library.catalog import tag_library
from backend.rfid.bambu_format import parse_tag_dump

router = APIRouter(prefix="/api/library", tags=["library"])


class DownloadRequest(BaseModel):
    material: str
    subtype: str
    color: str
    uid: str


@router.get("/status")
async def library_status():
    """Check if the library index is loaded."""
    return {
        "loaded": tag_library.is_loaded,
        "total": len(tag_library.catalog.entries),
    }


@router.post("/refresh")
async def refresh_index():
    """Refresh the catalog index from GitHub."""
    try:
        await tag_library.load_index(force_refresh=True)
        return {
            "total": len(tag_library.catalog.entries),
            "materials": tag_library.catalog.materials,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load index: {e}")


@router.get("/materials")
async def list_materials():
    """List all available material categories and their subtypes."""
    if not tag_library.is_loaded:
        await tag_library.load_index()
    return {"materials": tag_library.catalog.materials}


@router.get("/colors")
async def list_colors(material: str = Query(...), subtype: str = Query(...)):
    """List available colors for a material/subtype."""
    if not tag_library.is_loaded:
        await tag_library.load_index()
    colors = tag_library.get_colors(material, subtype)
    return {"colors": colors, "count": len(colors)}


@router.get("/search")
async def search_library(
    material: Optional[str] = None,
    subtype: Optional[str] = None,
    color: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Search the tag dump library with optional filters."""
    if not tag_library.is_loaded:
        await tag_library.load_index()

    results = tag_library.search(material=material, subtype=subtype, color=color, query=q)
    total = len(results)
    page = results[offset:offset + limit]

    # Deduplicate by material/subtype/color (show one entry per unique combo)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "entries": [e.to_dict() for e in page],
    }


@router.get("/browse")
async def browse_library(
    material: Optional[str] = None,
    subtype: Optional[str] = None,
):
    """Browse the library hierarchically — returns grouped entries."""
    if not tag_library.is_loaded:
        await tag_library.load_index()

    entries = tag_library.catalog.entries

    if material:
        entries = [e for e in entries if e.material == material]
    if subtype:
        entries = [e for e in entries if e.subtype == subtype]

    # Group by color
    grouped: dict[str, list[dict]] = {}
    for e in entries:
        if e.color not in grouped:
            grouped[e.color] = []
        grouped[e.color].append(e.to_dict())

    return {
        "material": material,
        "subtype": subtype,
        "colors": {color: {"count": len(dumps), "dumps": dumps[:3]}
                   for color, dumps in sorted(grouped.items())},
        "total": len(entries),
    }


@router.post("/download")
async def download_dump(req: DownloadRequest):
    """Download and parse a specific tag dump."""
    if not tag_library.is_loaded:
        await tag_library.load_index()

    # Find the entry
    matches = tag_library.search(
        material=req.material, subtype=req.subtype, color=req.color
    )
    entry = None
    for m in matches:
        if m.uid == req.uid:
            entry = m
            break

    if not entry:
        raise HTTPException(status_code=404, detail="Tag dump not found")

    try:
        dump_data = await tag_library.download_dump(entry)
        blocks = tag_library.dump_to_blocks(dump_data)

        # Parse the tag data
        fd = parse_tag_dump(blocks)

        # Convert blocks to hex for transport
        hex_blocks = [b.hex().upper() for b in blocks]

        return {
            "entry": entry.to_dict(),
            "card": dump_data.get("Card", {}),
            "filament": fd.to_dict(),
            "blocks": hex_blocks,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {e}")
