import os
import json
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
from loguru import logger as _logger

# Load .env once when this module is imported
load_dotenv(find_dotenv(), override=True)


@dataclass(frozen=True)
class Settings:
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "nebius")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "moonshotai/Kimi-K2-Instruct")

    EDGAR_API_KEY = os.getenv("EDGAR_API_KEY")
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

    TASK_CONFIG = {
        "env": "retail",
        "user_strategy": "llm",
        "user_model": f"{MODEL_NAME}",
        "user_provider": f"{MODEL_PROVIDER}",
        "task_split": "public",
        "task_path": "data/public.csv",
    }
    TASK_TEXT = f"""
        Your task is to instantiate the finance benchmark to test the agent located at
        the provided url.

        You should use the following env configuration:
        <env_config>
        {json.dumps(TASK_CONFIG, indent=2)}
        </env_config>
    """


# Create settings
settings = Settings()

def configure_logger():
    """
    Configure logger to be used - writes to both file and console
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "server.log"
    
    # idempotent config: remove existing handlers and add handlers
    _logger.remove()
    
    # Add file handler
    _logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
        rotation="10 MB",  # Rotate when file reaches 10MB
        retention="7 days",  # Keep logs for 7 days
        compression="zip",  # Compress old log files
        enqueue=True,  # Thread-safe logging
    )
    
    # Add console handler (optional - comment out if you don't want console output)
    _logger.add(
        lambda msg: print(msg, end=""),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
    )


# configure logger on import so other modules can `from .config import logger`
configure_logger()
logger = _logger