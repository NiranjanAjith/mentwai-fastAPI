# MentWai FastAPI Application

## Overview

MentWai is an AI-powered tutoring platform built with FastAPI. It provides personalized tutoring experiences by leveraging large language models, vector databases, and a modular agent architecture.

## Features

- **AI Tutoring**: Intelligent tutoring system that answers student questions
- **Jailbreak Detection**: Security system to prevent misuse of the AI
- **RAG Integration**: Retrieval-augmented generation for accurate, contextual responses
- **WebSocket Support**: Real-time communication between students and the AI tutor
- **S3 History Persistence**: Conversation history saved to AWS S3 for session continuity
- **Centralized Logging**: Standardized logging system across all application components
- **Performance Timing**: Execution time measurement for functions, tools, agents, and WebSockets

## Architecture

The application follows a modular architecture with the following components:

- **Framework**: Core abstractions for agents, contexts, and tools
- **Services**: Implementation of specific agents, contexts, and tools
- **API**: FastAPI endpoints for client communication
- **Prompts**: Jinja2 templates for LLM prompts

## Setup

### Prerequisites

- Python 3.9+
- PostgreSQL database
- AWS S3 bucket (for history persistence)
- Azure OpenAI API access
- Pinecone account (for vector database)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the required environment variables (see `.env.example`)

### Environment Variables

Create a `.env` file in the project root with the following variables:

```
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/mentwai

# Azure OpenAI Configuration
LANGUAGE_MODEL=Llama-3.3-70B-Instruct
VISION_MODEL=Llama-3.2-90B-Vision-Instruct
AZURE_ENDPOINT=your_azure_endpoint
AZURE_KEY=your_azure_key
AZURE_VERSION=your_azure_version

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key

# AWS S3 Configuration (for history persistence)
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_REGION=your_region
AWS_S3_BUCKET_NAME=your_bucket_name

# Security
SECRET_KEY=your_secret_key_for_jwt

# Logging (optional, defaults to INFO)
LOG_LEVEL=INFO
```

## Running the Application

```bash
uvicorn server:app --reload
```


## Testing

Run the tests with pytest:

```bash
python -m pytest -s
```

To test the S3 history persistence specifically:

```bash
python -m tests.s3_history_test
```

## License

[MIT License](LICENSE)