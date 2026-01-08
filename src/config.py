import os
import json
from dataclasses import dataclass

from dotenv import load_dotenv, find_dotenv
from loguru import logger as _logger

# Load .env once when this module is imported
load_dotenv(find_dotenv(), override=True)


@dataclass(frozen=True)
class Settings:
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "nebius")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "moonshotai/Kimi-K2-Instruct")

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
    Configure logger to be used
    """
    # idempotent config: remove existing handlers and add one handler
    _logger.remove()
    _logger.add(
        lambda msg: print(msg, end=""),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
    )


# configure logger on import so other modules can `from .config import logger`
configure_logger()
logger = _logger