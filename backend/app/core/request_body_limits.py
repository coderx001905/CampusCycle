import re
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException

from app.services.resource_images import MAX_IMAGE_BYTES, MAX_MULTIPART_OVERHEAD_BYTES

ASGIMessage = dict[str, Any]
Receive = Callable[[], Awaitable[ASGIMessage]]
Send = Callable[[ASGIMessage], Awaitable[None]]


class ResourceImageBodyLimitMiddleware:
    """Bound actual upload request bytes before multipart parsing can spool them."""

    def __init__(self, app: Any, *, api_prefix: str) -> None:
        self.app = app
        prefix = api_prefix.rstrip("/")
        self._upload_path = re.compile(rf"^{re.escape(prefix)}/resources/\d+/image$")
        self._max_body_bytes = MAX_IMAGE_BYTES + MAX_MULTIPART_OVERHEAD_BYTES

    async def __call__(self, scope: dict[str, Any], receive: Receive, send: Send) -> None:
        if (scope.get("type") != "http" or scope.get("method") != "POST" or
                self._upload_path.fullmatch(scope.get("path", "")) is None):
            await self.app(scope, receive, send)
            return

        received_bytes = 0

        async def limited_receive() -> ASGIMessage:
            nonlocal received_bytes
            message = await receive()
            if message.get("type") == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self._max_body_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail="Image upload request exceeds the allowed request size.",
                    )
            return message

        await self.app(scope, limited_receive, send)
