from __future__ import annotations

import os
import sys
from pathlib import Path

# Make the backend package importable.
BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))

# Use an in-memory DB and a temp work dir before app imports happen.
os.environ.setdefault("SO_DB_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SO_WORK_DIR", "/tmp/snapmaker-orca-api-tests")
os.environ.setdefault("SO_CORS_ORIGINS", "http://localhost:5173")
