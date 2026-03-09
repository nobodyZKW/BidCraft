from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router
from app.core.settings import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="采购文件智能生成系统 MVP",
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
