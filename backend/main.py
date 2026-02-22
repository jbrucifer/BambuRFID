"""
BambuRFID — Bambu Lab Filament Spool RFID Management Application.

FastAPI backend serving the web UI and providing APIs for:
- RFID tag reading, writing, and cloning via Android NFC bridge
- HKDF key derivation for MIFARE Classic authentication
- Tag data decoding/encoding (Bambu Lab proprietary format)
- Filament spool inventory management
- OpenSpool MQTT integration for direct printer communication
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import FRONTEND_DIR
from backend.spool.database import init_db, SessionLocal
from backend.spool.service import seed_default_presets
from backend.api import tags, spools, bridge, mqtt, library

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and seed defaults on startup."""
    logger.info("Starting BambuRFID...")
    init_db()
    db = SessionLocal()
    try:
        seed_default_presets(db)
    finally:
        db.close()
    logger.info("Database initialized, material presets seeded")
    yield
    logger.info("Shutting down BambuRFID")


app = FastAPI(
    title="BambuRFID",
    description="Bambu Lab Filament Spool RFID Management",
    version="1.0.0",
    lifespan=lifespan,
)

# Include API routers
app.include_router(tags.router)
app.include_router(spools.router)
app.include_router(bridge.router)
app.include_router(mqtt.router)
app.include_router(library.router)

# Serve frontend static files
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def index():
    """Serve the main frontend page."""
    return FileResponse(str(FRONTEND_DIR / "index.html"))
