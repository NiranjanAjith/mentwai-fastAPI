# Core Module

This directory contains core functionality for the AI Tutor service.

## Components

### `config.py`

Centralized configuration management that loads environment variables and provides application settings.

### `constants.py`

Defines constants used throughout the application, including response payload keys and logging constants.

### `logging.py`

Provides a centralized logging configuration for the entire application. This module ensures consistent log formatting and behavior across all components.

#### Usage

```python
# Initialize logging at application startup
from app.core.logging import setup_logging
from app.core.config import settings

# Configure with log level from settings
setup_logging(log_level=settings.LOG_LEVEL)

# Get a logger in any module
from app.core.logging import get_logger

logger = get_logger(__name__)

# Use the logger
logger.info("This is an info message")
logger.error("This is an error message")
logger.debug("This is a debug message")
```

### `responses.py`

Defines standard response formats for the API endpoints.