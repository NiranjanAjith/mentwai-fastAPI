import asyncio
import uuid
from datetime import datetime
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.tools.storage import storage_client
from app.services.context.tutor_context import TutorContext
from app.core.config import settings


async def test_s3_history_persistence():
    # Create a test session ID
    session_id = str(uuid.uuid4())
    print(f"Test session ID: {session_id}")
    
    # Create a context with the test session ID
    context = TutorContext(project_name="test")
    context.session_id = session_id
    
    # Add some test messages to history
    context.add_to_history("user", "Hello, this is a test message 1")
    context.add_to_history("assistant", "This is a test response 1")
    context.add_to_history("user", "Hello, this is a test message 2")
    context.add_to_history("assistant", "This is a test response 2")
    
    # Wait a moment for the async save to complete
    await asyncio.sleep(2)
    
    # Try to load the history from S3
    key = f"history_{session_id}.json"
    history_data = await asyncio.to_thread(storage_client.load, key)
    
    if history_data:
        print(f"Successfully loaded history from S3 with {len(history_data)} entries")
        for entry in history_data:
            print(f"[{entry['role']}] {entry['content']} ({entry['timestamp']})")
    else:
        print("Failed to load history from S3")
    
    # Clean up - delete the test history
    success = await asyncio.to_thread(storage_client.delete, key)
    if success:
        print(f"Successfully deleted test history from S3")
    else:
        print(f"Failed to delete test history from S3")


if __name__ == "__main__":
    # Check if AWS credentials are set
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY or not settings.AWS_S3_BUCKET_NAME:
        print("ERROR: AWS credentials or bucket name not set. Please set the following environment variables:")
        print("  - AWS_ACCESS_KEY_ID")
        print("  - AWS_SECRET_ACCESS_KEY")
        print("  - AWS_S3_BUCKET_NAME")
        print("  - AWS_REGION (optional, defaults to us-east-1)")
        sys.exit(1)
    
    # Run the test
    print(f"Testing S3 history persistence with bucket: {settings.AWS_S3_BUCKET_NAME}")
    asyncio.run(test_s3_history_persistence())