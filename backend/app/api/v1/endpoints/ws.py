"""
WebSocket endpoint for real-time updates.

Supports channel-based subscriptions:
- /api/v1/ws/deals       — deal stage changes, Kanban updates
- /api/v1/ws/extraction  — extraction progress
- /api/v1/ws/notifications — per-user notifications
- /api/v1/ws/properties  — property updates
- /api/v1/ws/analytics   — analytics report readiness

Authentication: pass JWT token as query parameter ``token``.
"""

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jwt.exceptions import PyJWTError
from loguru import logger

from app.core.config import settings
from app.core.security import _get_secret_key
from app.core.token_blacklist import token_blacklist
from app.services.websocket_manager import get_connection_manager

router = APIRouter()


async def _authenticate_token(token: str | None) -> int | None:
    """
    Validate a JWT token and return the user ID, or None for anonymous.

    This mirrors the logic in ``app.core.security.decode_token`` but is
    kept self-contained so the WS endpoint doesn't depend on async DB
    lookups during the handshake.

    Checks the token blacklist to reject revoked tokens (e.g. after logout).
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=[settings.ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            return None

        # Check if the specific token (by jti) has been blacklisted
        jti = payload.get("jti")
        if jti:
            try:
                if await token_blacklist.is_blacklisted(jti):
                    logger.warning(
                        f"WebSocket auth rejected: blacklisted token jti={jti[:8]}..."
                    )
                    return None
            except Exception as e:
                # Fail closed: reject token if blacklist check fails
                logger.error(f"WebSocket blacklist check error: {e}")
                return None

        return int(sub)
    except (PyJWTError, ValueError, TypeError, Exception):
        return None


@router.websocket("/ws/{channel}")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: str,
    token: str | None = Query(default=None),
) -> None:
    """
    WebSocket endpoint with channel subscription.

    Path params:
        channel: Channel name to subscribe to (deals, extraction, etc.)

    Query params:
        token: JWT access token for authentication (optional but recommended).

    Message protocol (client -> server):
        {"type": "pong"}                     — heartbeat response
        {"type": "subscribe", "channel": "x"} — subscribe to additional channel
        {"type": "unsubscribe", "channel": "x"} — leave a channel

    Message protocol (server -> client):
        {"type": "connected", ...}           — sent on successful connect
        {"type": "ping", ...}                — heartbeat; respond with pong
        {"type": "deal_update", ...}         — deal channel event
        {"type": "extraction_progress", ...} — extraction channel event
        {"type": "notification", ...}        — user notification
        {"type": "error", "message": "..."}  — error message
    """
    user_id = await _authenticate_token(token)

    manager = get_connection_manager()

    # Attempt to connect (may raise ValueError on limit exceeded)
    try:
        connection_id = await manager.connect(
            websocket, user_id=user_id, channels=[channel]
        )
    except ValueError as exc:
        # Reject the connection with a close reason
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close(code=1008, reason=str(exc))
        return

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "pong":
                await manager.handle_pong(connection_id)

            elif msg_type == "subscribe":
                target = data.get("channel")
                if target:
                    await manager.subscribe(connection_id, target)
                    await manager.send_to_connection(
                        connection_id,
                        {
                            "type": "subscribed",
                            "channel": target,
                        },
                    )

            elif msg_type == "unsubscribe":
                target = data.get("channel")
                if target:
                    await manager.unsubscribe(connection_id, target)
                    await manager.send_to_connection(
                        connection_id,
                        {
                            "type": "unsubscribed",
                            "channel": target,
                        },
                    )

            else:
                await manager.send_to_connection(
                    connection_id,
                    {
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    },
                )

    except WebSocketDisconnect:
        logger.debug(f"Client disconnected: {connection_id}")
    except Exception as e:
        logger.warning(f"WebSocket error for {connection_id}: {e}")
    finally:
        await manager.disconnect(connection_id)
