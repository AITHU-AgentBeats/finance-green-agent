import asyncio
from uuid import uuid4

import pytest

from .test_agent import send_text_message, validate_event


@pytest.mark.asyncio
async def test_sequential_tasks(agent):
    """Send a sequence of tasks to the agent and validate responses."""
    texts = [f"Task {i}" for i in range(1, 6)]
    all_errors = []

    for t in texts:
        events = await send_text_message(t, agent, context_id=uuid4().hex, streaming=False)
        assert events, "Agent should respond with at least one event"

        for event in events:
            # events may be Pydantic models or tuples (task, update)
            try:
                # model_dump available on pydantic models
                data = event.model_dump()
            except Exception:
                try:
                    data = event[0].model_dump()
                except Exception:
                    continue

            errors = validate_event(data)
            all_errors.extend(errors)

    assert not all_errors, "Message validation failed:\n" + "\n".join(all_errors)


@pytest.mark.asyncio
async def test_concurrent_tasks(agent):
    """Send multiple tasks concurrently to the agent and validate responses."""
    texts = [f"ConTask {i}" for i in range(1, 6)]
    ctxs = [uuid4().hex for _ in texts]

    coros = [
        send_text_message(t, agent, context_id=ctx, streaming=False) for t, ctx in zip(texts, ctxs)
    ]
    results = await asyncio.gather(*coros)

    all_errors = []
    for events in results:
        assert events, "Agent should respond with at least one event"
        for event in events:
            try:
                data = event.model_dump()
            except Exception:
                try:
                    data = event[0].model_dump()
                except Exception:
                    continue

            errors = validate_event(data)
            all_errors.extend(errors)

    assert not all_errors, "Concurrent message validation failed:\n" + "\n".join(all_errors)
