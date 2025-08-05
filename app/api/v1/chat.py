from uuid import uuid4, UUID
from typing import Dict
from datetime import datetime

from app.core.logging import Logger
logger = Logger(name="Chat")

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.orchestrator import TutorOrchestrator
from app.core.config import validate_token

router = APIRouter(prefix="/chat", tags=["chat"])
active_sessions: Dict[str, TutorOrchestrator] = {}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """ WebSocket endpoint for real-time chat with the AI tutor."""

    logger.info(f"[+] New WebSocket connection from {websocket.client.host} @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Extract query params
    student_id = websocket.query_params.get("student_id")
    textbook_id = websocket.query_params.get("textbook_id")
    token = websocket.query_params.get("token")
    debug = websocket.query_params.get("debug", "false").lower() == "true"
    session_id = websocket.query_params.get("session_id", uuid4())

    student_id = UUID(student_id)
    textbook_id = UUID(textbook_id)

    if not validate_token(token):
        await websocket.send_json({
            "error": "Invalid or expired token.",
            "code": 6001
        })
        logger.error(f"[!] Invalid token.")
        await websocket.close(code=4001)
        return
    else:
        await websocket.accept()
        logger.info(f"[+] Token validated successfully.")

    try:
        if session_id and session_id in active_sessions:
            # Reuse existing session
            orchestrator = active_sessions[session_id]
            session_id = session_id
            logger.info(f"[+] Reconnected to existing session {session_id}")
        else:
            # Create new session with the generated session_id
            orchestrator, log = await TutorOrchestrator.create(
                student_id=student_id, 
                textbook_id=textbook_id,
                session_id=session_id
            )
            active_sessions[session_id] = orchestrator
            logger.info(f"[+] New session {session_id}")
        
        await websocket.send_json({
            "is_end": True,
            "message": "Session Setup Complete",
            "status_code": 6000
        })
    except Exception as e:
        logger.error(f"[!] Failed to initialize session {session_id}: {e}")
        await websocket.send_json({
            "error": "Unable to initialize session.",
            "type": f"Exception: {e}",
            "code": 6001
        })
        await websocket.close(code=4002)
        return

    try:
        payload = {}
        while True:
            data: dict = await websocket.receive_json()
            user_query = data.get("message")
            images = data.get("images", [])

            request_start_time = datetime.now()
            async for response in orchestrator.run(user_query, images):
                if response:
                    payload["response"] = response
                    payload["response_type"] = type(response).__name__

                    await websocket.send_json(payload)

            payload = {
                "is_end": True,
                "session_id": str(session_id),
                "duration" : (datetime.now() - request_start_time).total_seconds(),
                "message": "Message Complete successfully."
            }
            if debug:
                payload["Log"] = log

            await websocket.send_json(payload)

    except WebSocketDisconnect:
        logger.info(f"[-] Session {session_id} disconnected @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    finally:
        active_sessions.pop(session_id, None)
        await orchestrator.close()
        logger.info(f"[-] WebSocket connection closed for {websocket.client.host} @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        await websocket.close()






# from sqlmodel import select
# from app.services.tools.tables.student import Student
# from app.services.tools.tables.textbook import TextBook
# from app.core.config import settings
# from fastapi import Query

# @router.get("/session-data")
# async def get_session_data(
#     student_id: str = Query(..., description="Student ID"),
#     textbook_id: str = Query(..., description="Textbook ID")
# ):
#     """
#     List student and textbook data for the given session.
#     """

#     student_id = UUID(student_id)
#     textbook_id = UUID(textbook_id)

#     async with settings.get_session() as session:
#         stmt = select(Student).where(Student.id == student_id)
#         result = await session.execute(stmt)
#         student = result.scalars().first()

#         statement = select(TextBook).where(TextBook.id == textbook_id)
#         result = await session.execute(statement)
#         textbook = result.scalars().first()

#     response = {}
#     if not student:
#         response["student error"] = "Student not found. (code: 6002)"
#         response["code"] = 6002
#     else:
#         response["student"] = student.model_dump()
#         response["code"] = 6000
#     if not textbook:
#         response["textbook error"] = "Textbook not found. (code: 6002)"
#         response["code"] = 6002
#     else:
#         response["textbook"] = textbook.model_dump()
#         response["code"] = 6000

#     return response
