"""
relay/server.py — Production Standalone Zero-Knowledge WebSocket Relay & Signaling Server

Run locally or inside Docker:
    python -m uvicorn relay.server:app --host 0.0.0.0 --port 8080
"""

import json
# pyrefly: ignore[missing-import]
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# pyrefly: ignore[missing-import]
from fastapi.responses import JSONResponse
import sys
from pathlib import Path

# Add project root to path if running directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.remote_relay_server import ZeroKnowledgeRelayServer


app = FastAPI(title="HONESTIC ATHENA Remote Relay", version="1.0.0")
relay_core = ZeroKnowledgeRelayServer()


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "athena-remote-relay",
        "active_clients": len(relay_core._connected_clients),
    }


@app.websocket("/ws/relay/{device_id}")
async def websocket_relay_endpoint(websocket: WebSocket, device_id: str):
    await websocket.accept()
    session = relay_core.register_client(device_id, websocket.send_text)

    try:
        while True:
            raw_text = await websocket.receive_text()
            # Relay frame to target recipient without inspecting payload
            response = await relay_core.route_frame(raw_text)
            if response.get("status") in ("ERROR", "REJECTED", "QUEUED_OFFLINE"):
                await websocket.send_text(json.dumps(response))
    except WebSocketDisconnect:
        relay_core.unregister_client(device_id)
    except Exception as e:
        print(f"[Relay] Error handling client {device_id}: {e}")
        relay_core.unregister_client(device_id)


if __name__ == "__main__":
    # pyrefly: ignore[missing-import]
    import uvicorn
    uvicorn.run("relay.server:app", host="0.0.0.0", port=8080, reload=False)

