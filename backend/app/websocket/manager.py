import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and per-server topic subscriptions."""

    def __init__(self) -> None:
        self._connections: Dict[WebSocket, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, initial_topic: str = "all") -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = {initial_topic}
        await self.send_personal(
            websocket,
            {
                "type": "connected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "subscriptions": [initial_topic],
            },
        )
        logger.info("WebSocket connected (active clients: %d)", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.pop(websocket, None)
        logger.info("WebSocket disconnected (active clients: %d)", len(self._connections))

    async def subscribe(self, websocket: WebSocket, topic: str) -> Set[str]:
        async with self._lock:
            topics = self._connections.setdefault(websocket, set())
            topics.add(topic)
            return set(topics)

    async def unsubscribe(self, websocket: WebSocket, topic: str) -> Set[str]:
        async with self._lock:
            topics = self._connections.setdefault(websocket, set())
            topics.discard(topic)
            return set(topics)

    async def send_personal(self, websocket: WebSocket, payload: Dict[str, Any]) -> None:
        try:
            await websocket.send_json(payload)
        except Exception:
            await self.disconnect(websocket)

    async def broadcast(self, payload: Dict[str, Any], server_id: str | None = None) -> None:
        async with self._lock:
            targets = [
                ws
                for ws, topics in self._connections.items()
                if "all" in topics or (server_id is not None and server_id in topics)
            ]

        if not targets:
            return

        stale: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)

        if stale:
            async with self._lock:
                for ws in stale:
                    self._connections.pop(ws, None)

    @property
    def active_count(self) -> int:
        return len(self._connections)


ws_manager = ConnectionManager()

