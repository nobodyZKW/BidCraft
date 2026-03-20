from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]


def _load_repo_api_key() -> str | None:
    config_path = ROOT_DIR / "config" / "config.py"
    if not config_path.exists():
        return None

    spec = importlib.util.spec_from_file_location("repo_config", config_path)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[assignment]
    key = getattr(module, "DEEPSEEK_API_KEY", None)
    if isinstance(key, str) and key.strip():
        return key.strip()
    fallback = getattr(module, "API_KEY", None)
    if isinstance(fallback, str) and fallback.strip():
        return fallback.strip()
    return None


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    data_dir: Path
    runtime_dir: Path
    export_dir: Path
    max_advance_payment_percent: int
    request_timeout_seconds: int


def _env(name: str, default: Any) -> Any:
    return os.getenv(name, default)


def load_settings() -> Settings:
    repo_key = _load_repo_api_key() or ""
    if not repo_key:
        raise ValueError(
            "Missing DEEPSEEK_API_KEY in config/config.py. "
            "All API key usage is configured to read from this file."
        )
    data_dir = ROOT_DIR / "data"
    runtime_dir = data_dir / "runtime"
    export_dir = ROOT_DIR / "exports"

    runtime_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        app_name="BidCraft AI",
        app_version="1.0.0-mvp",
        deepseek_api_key=repo_key,
        deepseek_base_url=str(_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")),
        deepseek_model=str(_env("DEEPSEEK_MODEL", "deepseek-chat")),
        data_dir=data_dir,
        runtime_dir=runtime_dir,
        export_dir=export_dir,
        max_advance_payment_percent=int(_env("MAX_ADVANCE_PAYMENT_PERCENT", 50)),
        request_timeout_seconds=int(_env("REQUEST_TIMEOUT_SECONDS", 30)),
    )


settings = load_settings()
