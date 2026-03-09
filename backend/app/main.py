from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.settings import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Procurement document generation MVP",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.mount("/exports", StaticFiles(directory=settings.export_dir), name="exports")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
