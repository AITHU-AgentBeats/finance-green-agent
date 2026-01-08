from typing import Any
from pydantic import BaseModel, HttpUrl, ValidationError
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, TaskState, SendMessageSuccessResponse
from a2a.utils import get_message_text, new_agent_text_message

from messenger import Messenger
from dataset import DatasetLoader

from utils import send_message, get_text_parts
from config import logger


class EvalRequest(BaseModel):
    """Request format sent by the AgentBeats platform to green agents."""
    participants: dict[str, HttpUrl] # role -> agent URL
    config: dict[str, Any]


class Agent:
    # Each request handles a single purple agent to be evaluated
    required_roles: list[str] = ["agent"]
    # The request should list the tasks the agent would like to be evaluated at
    required_config_keys: list[str] = []

    def __init__(self, path : str):
        self.messenger = Messenger()
        # Initialize other state here
        self.dataset = DatasetLoader(path)

    def validate_request(self, request: EvalRequest) -> tuple[bool, str]:
        missing_roles = set(self.required_roles) - set(request.participants.keys())
        if missing_roles:
            return False, f"Missing roles: {missing_roles}"

        missing_config_keys = set(self.required_config_keys) - set(request.config.keys())
        if missing_config_keys:
            return False, f"Missing config keys: {missing_config_keys}"

        return True, "ok"

    async def run(self, message: Message, updater: TaskUpdater) -> None:
        """Implement your agent logic here.

        Args:
            message: The incoming message
            updater: Report progress (update_status) and results (add_artifact)

        Use self.messenger.talk_to_agent(message, url) to call other agents.
        """
        input_text = get_message_text(message)

        try:
            request: EvalRequest = EvalRequest.model_validate_json(input_text)
            ok, msg = self.validate_request(request)
            if not ok:
                await updater.reject(new_agent_text_message(msg))
                return
        except ValidationError as e:
            await updater.reject(new_agent_text_message(f"Invalid request: {e}"))
            return

        # ok
        await self.evaluate(request, updater)


    async def evaluate(self, request: EvalRequest, updater: TaskUpdater) -> None:
        """Execute the evaluation logic."""
        # Get the purple agent URL
        agent_url = str(request.participants["agent"])
        logger.info(f"Starting evaluation of {agent_url}")

        # Get configuration with defaults
        type = request.config.get("type")

        # Get tasks per question type (or all)
        # TODO
        tasks = ...

        await updater.update_status(
            TaskState.working,
            new_agent_text_message(f"Starting evaluation of {len(tasks)} financial research tasks")
        )
        for task in tasks:
            results = await self.ask_agent_to_solve(
                agent_url=agent_url,
                task_description=task
            )

    async def ask_agent_to_solve(self, agent_url:str, task_description:str):
        """
        Asks tto be solved
        """
        # Prepare the initial message to the white agent
        context_id = None

        logger.info(
            f"Sending task {task_description}"
        )
        white_agent_response = await send_message(
            agent_url, task_description, context_id=context_id
        )
        res_root = white_agent_response.root
        assert isinstance(res_root, SendMessageSuccessResponse)
        res_result = res_root.result
        assert isinstance(
            res_result, Message
        )  # though, a robust design should also support Task
        if context_id is None:
            context_id = res_result.context_id
        else:
            assert context_id == res_result.context_id, (
                "Context ID should remain the same in a conversation"
            )

        text_parts = get_text_parts(res_result.parts)
        assert len(text_parts) == 1, "Expecting exactly one text part from the white agent"
        white_text = text_parts[0]
        logger.debug(f"@@@ White agent response:\n{white_text}")

        return white_text
