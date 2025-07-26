# import pytest
# from fastapi import WebSocket
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

def test_invalid_token_ws():
    with client.websocket_connect(
        "/api/chat/ws?student_id=test_student&textbook_id=test_book&token=invalid"
    ) as websocket:
        data = websocket.receive_json()
        assert data["error"] == "Invalid or expired token."
        assert data["code"] == 6001

def test_missing_params_ws():
    with client.websocket_connect("/api/chat/ws") as websocket:
        data = websocket.receive_json()
        assert data["error"] == "Invalid or expired token."
        assert data["code"] == 6001

import base64

client = TestClient(app)

def test_interactive_ws():
    """Interactive test: send custom queries to the WebSocket and print responses."""
    student_id = "test_student"
    textbook_id = "test_book"
    token = "invalid"  # Use a valid token if available

    ws_url = f"/api/chat/ws?student_id={student_id}&textbook_id={textbook_id}&token={token}"

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
            try:
                response = websocket.receive_json()
                print("✅ Received:", response)
            except Exception as e:
                print(f"❌ Error receiving response: {e}")

# You can add more tests for valid tokens and orchestrator logic by mocking dependencies.