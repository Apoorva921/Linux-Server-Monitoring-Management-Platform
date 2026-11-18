from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_access_token
from app.websocket.manager import ws_manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/metrics")
async def websocket_metrics(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None),
    server_id: Optional[str] = Query(default="all"),
) -> None:
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
        return

    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
        return

    initial_topic = server_id or "all"
    await ws_manager.connect(websocket, initial_topic=initial_topic)
    try:
        while True:
            message = await websocket.receive_json()
            action = message.get("action")
            if action == "ping":
                await ws_manager.send_personal(
                    websocket,
                    {"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()},
                )
            elif action == "subscribe":
                topic = str(message.get("server_id") or "all")
                topics = await ws_manager.subscribe(websocket, topic)
                await ws_manager.send_personal(
                    websocket,
                    {"type": "subscribed", "subscriptions": sorted(topics)},
                )
            elif action == "unsubscribe":
                topic = str(message.get("server_id") or "all")
                topics = await ws_manager.unsubscribe(websocket, topic)
                await ws_manager.send_personal(
                    websocket,
                    {"type": "unsubscribed", "subscriptions": sorted(topics)},
                )
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)

