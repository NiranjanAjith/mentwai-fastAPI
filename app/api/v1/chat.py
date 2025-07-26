import logging
import uuid
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.orchestrator import TutorOrchestrator
from app.core.config import validate_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

active_sessions: Dict[str, TutorOrchestrator] = {}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Extract query params manually
    student_id = websocket.query_params.get("student_id")
    textbook_id = websocket.query_params.get("textbook_id")
    token = websocket.query_params.get("token")
    await websocket.accept()
    session_id = str(uuid.uuid4())

    if not validate_token(token):
        await websocket.send_json({
            "error": "Invalid or expired token.",
            "code": 6001
        })
        await websocket.close(code=4001)
        return

    try:
        orchestrator = TutorOrchestrator(student_id=student_id, textbook_id=textbook_id)
        active_sessions[session_id] = orchestrator
        logger.info(f"[+] New session {session_id}")

    except Exception as e:
        logger.error(f"[!] Failed to initialize session {session_id}: {e}")
        await websocket.send_json({
            "error": "Unable to initialize session.",
            "code": 6001
        })
        await websocket.close(code=4002)
        return

    try:
        while True:
            data = await websocket.receive_json()
            user_query = data.get("message")

            async for response in orchestrator.run(user_query):
                await websocket.send_json({"response": response})

    except WebSocketDisconnect:
        logger.info(f"[-] Session {session_id} disconnected.")
    finally:
        #TODO: Save session history
        await websocket.close()
        active_sessions.pop(session_id, None)
