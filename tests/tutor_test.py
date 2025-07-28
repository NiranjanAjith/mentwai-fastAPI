# import pytest
# from fastapi import WebSocket
from fastapi.testclient import TestClient
from server import app
import base64

client = TestClient(app)

student_id = "0148e9a4-91fd-4c32-8d43-0c7005b0b7b3"
textbook_id = "9e3628e8-8114-4db4-99a7-bf72710037d8"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY4ODkyMDI2LCJpYXQiOjE3NTA3NDgwMjYsImp0aSI6IjNlZDg0ZmJlOWRkMTQ3MDFiZDIwZDMwMDc4N2FmMTM0IiwidXNlcl9pZCI6Mn0.-tTDzztYwVq1558NUN8CLMYVUY4OskQZX-lpEH8ZV_I"

def test_invalid_token_ws():
    with client.websocket_connect(
        f"/api/v1/chat/ws?student_id={student_id}&textbook_id={textbook_id}&token=token"
    ) as websocket:
        data = websocket.receive_json()

def test_session_data_invalid_token():
    response = client.get(
        "/api/v1/chat/session-data",
        params={
            "student_id": student_id,
            "textbook_id": textbook_id,
            "token": token
        }
    )
    
    data = response.json()



def test_interactive_ws():
    """Interactive test: send custom queries to the WebSocket and print responses."""
    ws_url = f"/api/v1/chat/ws?student_id={student_id}&textbook_id={textbook_id}&token={token}"

    with client.websocket_connect(ws_url) as websocket:
        print("\n🔄 Enter queries to test the WebSocket. Type 'exit' to stop.\n")
        while True:
            query = input("\nYour Query: ").strip()
            if query.lower() == "exit":
                print("\n👋 Exiting interactive mode.\n")
                break

            # Example: send images as base64 if needed
            # with open("path/to/image.png", "rb") as image_file:
            #     image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
            #     payload = {"message": query, "images": [image_base64]}
            # else:
            payload = {"message": query}

            websocket.send_json(payload)
            response = {}
            while True:
                try:
                    response = websocket.receive_json()
                    print("✅ Received:", response)
                    print("type: ", type(response).__name__)
                except Exception as e:
                    print(f"❌ Error receiving response: {e}")
                    print("type: ", type(response).__name__)
                if "error" in response:
                    break

# You can add more tests for valid tokens and orchestrator logic by mocking dependencies.