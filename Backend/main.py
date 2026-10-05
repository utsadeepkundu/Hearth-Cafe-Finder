import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from Backend.places import router as places_router


BASE_DIR = Path(__file__).resolve().parents[1]
UI_FILE = BASE_DIR / "UI" / "index.html"

app = FastAPI(
    title="Hearth API",
    version="1.0.0",
    description="Nearby places discovery API for the Hearth web application.",
)

cors_origins_raw = os.getenv("CORS_ORIGINS", "*")
cors_origins = [
    origin.strip()
    for origin in cors_origins_raw.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def home():
    """Serve the Hearth frontend from the FastAPI application."""
    if not UI_FILE.is_file():
        return {
            "message": "Hearth API is running, but UI/index.html was not found."
        }

    return FileResponse(
        UI_FILE,
        media_type="text/html",
    )


@app.get("/api/health")
async def health():
    """Basic health check for local development and deployment monitoring."""
    return {
        "status": "healthy",
        "service": "Hearth API",
    }


app.include_router(
    places_router,
    prefix="/api",
)
