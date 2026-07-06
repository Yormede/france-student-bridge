import os
import sys
import platform
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MACOS = platform.system() == "Darwin"

if IS_WINDOWS:
    import asyncio
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

API_BASE_URL = "https://api.francestudent.org"
FRONTEND_URL = "https://ia.francestudent.org"
AUTH_API_URL = f"{FRONTEND_URL}/api/auth"

AUTH_EMAIL = os.environ.get("FS_EMAIL", "")
AUTH_PASSWORD = os.environ.get("FS_PASSWORD", "")

STORAGE_DIR = BASE_DIR / "storage"
IMAGES_DIR = STORAGE_DIR / "images"
STORE_FILE = BASE_DIR / "store.json"

REQUEST_TIMEOUT = 120
SSE_TIMEOUT = 60
SSE_RECONNECT_TIMEOUT = 30

MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 10]

SERVER_HOST = os.environ.get("BIND_HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("BIND_PORT", "8765"))

DEFAULT_AGENT_ID = None
MODEL_REFRESH_INTERVAL = 3600

IMAGES_DIR.mkdir(parents=True, exist_ok=True)
