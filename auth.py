import time
import json
import httpx
from config.config import (
    AUTH_EMAIL, AUTH_PASSWORD, API_BASE_URL, FRONTEND_URL,
    AUTH_API_URL, STORE_FILE, REQUEST_TIMEOUT
)


class AuthManager:
    def __init__(self):
        self._token = None
        self._expires_at_sec = 0
        self._pending = None
        self._client = httpx.Client(timeout=REQUEST_TIMEOUT)
        self._load_store()

    @property
    def token(self):
        return self._token

    @property
    def is_authenticated(self):
        return self._token is not None and not self._is_expired()

    def _is_expired(self):
        return time.time() + 30 >= self._expires_at_sec

    def _load_store(self):
        if STORE_FILE.exists():
            try:
                data = json.loads(STORE_FILE.read_text())
                self._token = data.get("token")
                self._expires_at_sec = data.get("expires_at_sec", 0)
            except Exception:
                pass

    def _save_store(self):
        STORE_FILE.write_text(json.dumps({
            "token": self._token,
            "expires_at_sec": self._expires_at_sec,
        }))

    def _login_via_api(self):
        r = self._client.post(
            f"{API_BASE_URL}/user/login",
            json={"email": AUTH_EMAIL, "password": AUTH_PASSWORD},
        )
        r.raise_for_status()
        data = r.json()
        self._token = data["token"]
        self._expires_at_sec = time.time() + 86400
        self._save_store()
        return self._token

    def _get_token_via_nextauth(self):
        r = self._client.get(
            f"{AUTH_API_URL}/api-token",
            cookies=self._client.cookies,
        )
        r.raise_for_status()
        data = r.json()
        self._token = data["accessToken"]
        self._expires_at_sec = data["expiresAt"]
        self._save_store()
        return self._token

    def _do_auth_flow(self):
        try:
            return self._login_via_api()
        except Exception:
            pass
        try:
            return self._get_token_via_nextauth()
        except Exception:
            pass
        raise RuntimeError(
            "Impossible de s'authentifier. Vérifie FS_EMAIL / FS_PASSWORD "
            "ou fournis un cookie de session NextAuth."
        )

    def get_token(self, force=False):
        if force:
            self._token = None
            self._expires_at_sec = 0

        if self._token and not self._is_expired():
            return self._token

        if self._pending is not None:
            return self._pending

        self._pending = self._do_auth_flow()
        token = self._pending
        self._pending = None
        return token

    def get_headers(self):
        token = self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream, application/json",
        }

    def clear(self):
        self._token = None
        self._expires_at_sec = 0
        if STORE_FILE.exists():
            STORE_FILE.unlink()
