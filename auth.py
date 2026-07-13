import time
import json
import subprocess
import base64
import os
from pathlib import Path
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

    def _parse_jwt_expiry(self, token):
        """Extract expiry timestamp from JWT payload."""
        try:
            parts = token.split('.')
            payload_b64 = parts[1] + '=' * (4 - len(parts[1]) % 4)
            data = json.loads(base64.urlsafe_b64decode(payload_b64))
            return data.get('exp', time.time() + 300)
        except Exception:
            return time.time() + 300

    def _login_via_puppeteer(self):
        """Get JWT via Puppeteer headless SSO flow (WHMCS -> IA portal)."""
        script_path = Path(__file__).parent / "get_jwt.js"
        if not script_path.exists():
            raise RuntimeError(f"get_jwt.js introuvable: {script_path}")

        env = os.environ.copy()
        env["FS_EMAIL"] = AUTH_EMAIL
        env["FS_PASSWORD"] = AUTH_PASSWORD

        print("[AUTH] Lancement Puppeteer SSO...")
        result = subprocess.run(
            ["node", str(script_path)],
            capture_output=True, text=True, timeout=120,
            env=env,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Puppeteer SSO echoue: {result.stderr.strip()}")

        token = result.stdout.strip()
        if not token or len(token) < 50:
            raise RuntimeError(f"JWT invalide depuis Puppeteer: {token[:30]}...")

        self._token = token
        self._expires_at_sec = self._parse_jwt_expiry(token)
        self._save_store()
        print(f"[AUTH] JWT obtenu (expire dans {int(self._expires_at_sec - time.time())}s)")
        return self._token

    def _get_token_via_nextauth(self):
        """Fallback: get JWT if NextAuth session cookies are present."""
        r = self._client.get(
            f"{AUTH_API_URL}/api-token",
            cookies=self._client.cookies,
        )
        r.raise_for_status()
        data = r.json()
        self._token = data["accessToken"]
        self._expires_at_sec = data.get("expiresAt", self._parse_jwt_expiry(self._token))
        self._save_store()
        return self._token

    def _do_auth_flow(self):
        # 1. Puppeteer SSO (primary)
        try:
            return self._login_via_puppeteer()
        except Exception as e:
            print(f"[AUTH] Puppeteer echoue: {e}")

        # 2. NextAuth cookies (fallback)
        try:
            return self._get_token_via_nextauth()
        except Exception as e:
            print(f"[AUTH] NextAuth fallback echoue: {e}")

        raise RuntimeError(
            "Impossible de s'authentifier. Verifie FS_EMAIL / FS_PASSWORD."
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
