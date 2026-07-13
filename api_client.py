import uuid as uuid_mod
from config.config import API_BASE_URL, REQUEST_TIMEOUT, SSE_TIMEOUT
from sse_parser import parse_sse_stream


class FranceStudentAPI:
    def __init__(self, auth):
        self._auth = auth

    def _headers(self):
        return self._auth.get_headers()

    async def get_models(self):
        import httpx
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as c:
            r = await c.get(
                f"{API_BASE_URL}/chats/agents?include-disabled=false",
                headers=self._headers(),
            )
            r.raise_for_status()
            agents = r.json()
            return [
                {
                    "id": a["id"],
                    "name": a["name"],
                    "description": a.get("description", ""),
                    "model": a.get("model", ""),
                    "modelProvider": a.get("modelProvider", ""),
                    "isActive": a.get("isActive", False),
                    "isDefault": a.get("isDefault", False),
                }
                for a in agents
                if a.get("isActive")
            ]

    async def create_chat(self, message, agent_id=None, images=None, files=None,
                          enable_web_search=False):
        import httpx
        body = {
            "agentId": agent_id,
            "initialContent": message,
            "images": images or [],
            "enableWebSearch": enable_web_search,
            "isIncognito": False,
            "isPrivate": True,
        }
        async with httpx.AsyncClient(timeout=SSE_TIMEOUT) as c:
            async with c.stream(
                "POST",
                f"{API_BASE_URL}/chats/stream",
                headers=self._headers(),
                json=body,
            ) as r:
                r.raise_for_status()
                events = []
                async for ev in parse_sse_stream(r):
                    events.append(ev)
                return events

    async def send_message(self, chat_id, message, images=None, files=None,
                           enable_web_search=False):
        import httpx
        body = {
            "content": message,
            "images": images or [],
            "enableWebSearch": enable_web_search,
        }
        async with httpx.AsyncClient(timeout=SSE_TIMEOUT) as c:
            async with c.stream(
                "POST",
                f"{API_BASE_URL}/chats/{chat_id}",
                headers=self._headers(),
                json=body,
            ) as r:
                r.raise_for_status()
                events = []
                async for ev in parse_sse_stream(r):
                    events.append(ev)
                return events

    async def reconnect_stream(self, chat_id, last_event_id):
        import httpx
        headers = {
            **self._headers(),
            "Last-Event-ID": str(last_event_id),
        }
        async with httpx.AsyncClient(timeout=SSE_TIMEOUT) as c:
            async with c.stream(
                "GET",
                f"{API_BASE_URL}/chats/{chat_id}/stream",
                headers=headers,
                params={"last_event_id": last_event_id},
            ) as r:
                r.raise_for_status()
                events = []
                async for ev in parse_sse_stream(r):
                    events.append(ev)
                return events

    async def get_chat(self, chat_id):
        import httpx
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as c:
            r = await c.get(
                f"{API_BASE_URL}/chats/{chat_id}",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def get_chats(self, limit=20, cursor_chat_id=None):
        import httpx
        params = {"limit": limit}
        if cursor_chat_id:
            params["cursor_chat_id"] = cursor_chat_id
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as c:
            r = await c.get(
                f"{API_BASE_URL}/chats",
                headers=self._headers(),
                params=params,
            )
            r.raise_for_status()
            return r.json()

    async def delete_chat(self, chat_id):
        import httpx
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as c:
            r = await c.delete(
                f"{API_BASE_URL}/chats/{chat_id}",
                headers=self._headers(),
            )
            r.raise_for_status()

    async def get_chat_usage(self, chat_id):
        import httpx
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as c:
            r = await c.get(
                f"{API_BASE_URL}/chats/{chat_id}/usage",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def upload_file(self, file_path):
        import httpx
        from pathlib import Path
        file_path = Path(file_path)
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as c:
            with open(file_path, "rb") as f:
                r = await c.post(
                    f"{API_BASE_URL}/filesv2",
                    headers={"Authorization": self._headers()["Authorization"]},
                    files={"file": (file_path.name, f, "application/octet-stream")},
                )
            r.raise_for_status()
            return r.json()

    async def get_image(self, chat_id, message_id, image_id):
        import httpx
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as c:
            r = await c.get(
                f"{API_BASE_URL}/chats/{chat_id}/messages/{message_id}/images/{image_id}",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.content, r.headers.get("content-type", "image/png")
