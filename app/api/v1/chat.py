import logging
from uuid import uuid4, UUID
from typing import Dict
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.orchestrator import TutorOrchestrator
from app.core.config import validate_token

router = APIRouter(prefix="/chat", tags=["chat"])
active_sessions: Dict[str, TutorOrchestrator] = {}
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Extract query params manually
    student_id = websocket.query_params.get("student_id")
    textbook_id = websocket.query_params.get("textbook_id")
    token = websocket.query_params.get("token")
    debug = websocket.query_params.get("debug", "false").lower() == "true"
    await websocket.accept()
    session_id = str(uuid4())

    student_id = UUID(student_id)
    textbook_id = UUID(textbook_id)

    if not validate_token(token):
        await websocket.send_json({
            "error": "Invalid or expired token.",
            "code": 6001
        })
        await websocket.close(code=4001)
        return

    try:
        orchestrator, log = await TutorOrchestrator.create(student_id=student_id, textbook_id=textbook_id)
        active_sessions[session_id] = orchestrator
        logger.info(f"[+] New session {session_id}")
        await websocket.send_json({
            "log": log
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
            data = await websocket.receive_json()
            user_query = data.get("message")
            print(f"Received query: {user_query}\n******************************************************************")

            async for response in orchestrator.run(user_query):
                if response:
                    payload["response"] = response
                    payload["response_type"] = type(response).__name__
                    if debug:
                        payload["Log"] = log

                    await websocket.send_json(payload)

            end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await websocket.send_json({
                "is_end": True,
                "session_id": session_id,
                "start_time": start_time,
                "end_time": end_time,
                "message": "Message Complete successfully."
            })

    except WebSocketDisconnect:
        logger.info(f"[-] Session {session_id} disconnected.")
    finally:
        await websocket.close()
        active_sessions.pop(session_id, None)



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
