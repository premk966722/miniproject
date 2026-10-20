from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

APP_NAME = os.getenv("APP_NAME", "TAX-SHIELD")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).resolve().parents[2] / "data")))
DB_PATH = Path(os.getenv("DB_PATH", str(DATA_DIR / "tax_shield.db")))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ADMIN_API_KEY: Optional[str] = os.getenv("ADMIN_API_KEY")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
MAX_REQUEST_BYTES = int(os.getenv("MAX_REQUEST_BYTES", str(1024 * 1024)))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

if "*" in CORS_ORIGINS:
	raise ValueError("CORS_ORIGINS must list explicit origins; wildcard origins are not supported.")
if ENVIRONMENT.lower() == "production" and (not ADMIN_API_KEY or len(ADMIN_API_KEY) < 32):
	raise ValueError("Production requires an ADMIN_API_KEY of at least 32 characters.")
