import time
from typing import Any
from pydantic import BaseModel, HttpUrl, ValidationError
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, TaskState, SendMessageSuccessResponse, Part, DataPart
from a2a.utils import get_message_text, new_agent_text_message

from messenger import Messenger
from dataset import DatasetLoader
from judge import Judge
from utils import send_message
from config import logger, settings


class EvalRequest(BaseModel):
    """Request format sent by the AgentBeats platform to green agents."""

    participants: dict[str, HttpUrl]  # role -> agent URL
    config: dict[str, Any]


class Agent:
    """
    Agent class defining the procedure to assess target agent accuracy
    """

    # Each request handles a single purple agent to be evaluated
    required_roles: list[str] = ["purple_agent"]
    # The request should list the tasks the agent would like to be evaluated at
    required_config_keys: list[str] = []

    def __init__(self, path: str):
        self.messenger = Messenger()
        # Initialize other state here
        self.dataset = DatasetLoader(path)

    def validate_request(self, request: EvalRequest) -> tuple[bool, str]:
        """
        Validates that the request has the required role "purple_agent" and "config" params
        """
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
        agent_url = str(request.participants["purple_agent"])
        logger.info(f"Starting evaluation of {agent_url}")

        # Get configuration with defaults
        type = request.config.get("type")
        query_index = request.config.get("query_index")

        # Get query per question type (or all)
        queries = self.dataset.get_queries(question_type=type)

        # If query_index is specified, run only that query
        if query_index is not None:
            try:
                query_index = int(query_index)
                if 0 <= query_index < len(queries):
                    queries = [queries[query_index]]
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            f"Running single query at index {query_index}: {queries[0].question[:100]}..."
                        ),
                    )
                else:
                    await updater.reject(
                        new_agent_text_message(
                            f"Invalid query_index {query_index}. Valid range: 0-{len(queries) - 1}"
                        )
                    )
                    return
            except (ValueError, TypeError):
                await updater.reject(
                    new_agent_text_message(
                        f"Invalid query_index: {query_index}. Must be an integer."
                    )
                )
                return
        else:
            await updater.update_status(
                TaskState.working,
                new_agent_text_message(
                    f"Starting evaluation of {len(queries)} financial research queries"
                ),
            )

        benchmark_results = {}
        for q in queries:
            # Start
            timestamp_started = time.time()
            results = await self.send_query(agent_url=agent_url, request=q.question)
            time_taken = (time.time() - timestamp_started) / 60  # mins

            # Evaluate the response
            judge = Judge(q, time_taken, model=settings.MODEL_NAME)
            judge.judge(response=results)

            evals = judge.return_eval()

            benchmark_results[q.id] = evals

        logger.debug(f"Obtained results {len(benchmark_results)}")

        flattened_results = self.average_results(benchmark_results)
        logger.debug(flattened_results)

        # Add benchmark as result
        await updater.add_artifact(
            parts=[
                Part(root=DataPart(data=flattened_results)),
            ],
            name="Result",
        )

    def average_results(self, list_results: list[dict]) -> dict:
        """
        Gets the final answer if more than one query is involved
        """
        final_results = {"num_queries" : len(list_results)}

        # Normalize input to a list of dicts
        entries = list(list_results.values()) if isinstance(list_results, dict) else list(list_results)
        if not entries:
            return final_results

        def is_number(x):
            return isinstance(x, (int, float)) and not isinstance(x, bool)

        def avg(values):
            # All dicts -> recurse to average nested structure
            if all(isinstance(v, dict) for v in values):
                return self.average_results({i: v for i, v in enumerate(values)})
            # All numeric -> return mean
            if all(is_number(v) for v in values):
                return sum(float(v) for v in values) / len(values)
            # Fallback: return unique values (single value -> scalar)
            uniq = []
            seen = set()
            for v in values:
                key = str(v)
                if key not in seen:
                    seen.add(key)
                    uniq.append(v)
            return uniq[0] if len(uniq) == 1 else uniq

        # Collect all keys and compute per-key averages
        keys = set()
        for e in entries:
            if isinstance(e, dict):
                keys.update(e.keys())

        for k in keys:
            vals = [e.get(k) for e in entries]
            final_results[k] = avg(vals)

        return final_results

    async def send_query(self, agent_url: str, request: str):
        """
        Sends a query to the purple agent and returns the response
        """
        # Prepare the initial message to the purple agent
        context_id = None

        logger.debug(f"[PURPLE AGENT REQUEST] URL: {agent_url}")
        logger.debug(f"[PURPLE AGENT REQUEST] Query: {request}")
        logger.debug(f"[PURPLE AGENT REQUEST] Context ID: {context_id}")

        agent_response = await send_message(agent_url, request, context_id=context_id)

        # Is a success response
        res_root = agent_response.root
        assert isinstance(res_root, SendMessageSuccessResponse)

        # Extract content
        res_result = res_root.result
        artifact = res_result.artifacts[0]

        # First artifact, second part
        _, response = artifact.parts
        response_dict = response.root.data

        logger.debug(f"[PURPLE AGENT RESPONSE] URL: {agent_url}")
        logger.debug(f"[PURPLE AGENT RESPONSE] Response data: {response_dict}")

        if "response" in response_dict:
            purple_response = response_dict["response"]
            logger.debug(
                f"[PURPLE AGENT RESPONSE] Extracted response text: {purple_response[:200]}..."
                if len(purple_response) > 200
                else f"[PURPLE AGENT RESPONSE] Extracted response text: {purple_response}"
            )
            return purple_response

        logger.warning(
            f"[PURPLE AGENT RESPONSE] No 'response' key found in response_dict: {response_dict}"
        )
        return "something went wrong"
