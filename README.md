# Finance Benchmarking Green Agent

This repository contains an agent implementation and harness for the finance benchmarking tasks. It implements a Model Context Protocol (MCP) style architecture where tasks are issued to agents, adjudicated by judge workers, and executed by the agent runtime.

Goals
- Provide a reproducible agent runtime for the finance benchmark.
- Support automated A2A (agent-to-agent) evaluation flows.
- Allow pluggable judge models and task configuration.

This works takes the benchmark in https://arxiv.org/abs/2508.00828.

The original code for the dataset is in https://github.com/vals-ai/finance-agent

**Project layout**

```
src/
├─ agent.py        # core agent logic and task handling helpers
├─ server.py       # HTTP A2A server exposing the agent endpoint
├─ messenger.py    # messaging utilities for A2A payloads
├─ judge.py        # judge worker that evaluates runs
├─ mcp_server.py   # Model Context Protocol helper / client
├─ dataset.py      # dataset loading (data/public.csv)
├─ config.py       # configuration and .env loading
└─ utils.py
data/
└─ public.csv      # default public tasks used by MCP
tests/             # unit & integration tests (A2A conformance)
Dockerfile
pyproject.toml
README.md
```

**High-level architecture**

```
Simple architecture (ASCII)

+-----------------+         +---------------+
| External Runner |  --->   |  MCP Server   |
+-----------------+         +---------------+
                                |   ^
                                v   |
                            +---------------+
                            |  Agent Server |
                            +---------------+
                               |
                                v
                          +---------+
                          |  Judge  |
                          +---------+
```

What this shows
- The MCP Server coordinates tasks and aggregates results.
- The Agent HTTP endpoint receives A2A tasks and runs them through the runtime.
- The judge in `judge.py` evaluates agent outputs and returns scores.

## Running Locally

```bash
# Install dependencies
uv sync

# Run the server
uv run src/server.py
```

## Running with Docker

```bash
# Build the image
docker build -t my-agent .

# Run the container
docker run -p 9009:9009 my-agent
```

## Configuration

Add an `.env` file to the project root or export the variables in your environment. The main keys read from `src/config.py` are listed below with their defaults.

- `LOG_LEVEL` — log verbosity (default: `INFO`)
- `NEBIUS_API_KEY` — API key for Nebius model provider (required if using Nebius)
- `MODEL_PROVIDER` — which model provider to use (default: `nebius`)
- `MODEL_NAME` — model name to use for task execution (default: `moonshotai/Kimi-K2-Instruct`)
- `EDGAR_API_KEY` — optional EDGAR API key used by data helpers
- `SERPAPI_API_KEY` — optional SerpAPI key used by data helpers

### Example `.env`
```bash
LOG_LEVEL=DEBUG
NEBIUS_API_KEY=sk-XXXXXXXXXXXXXXXXXXXX
MODEL_PROVIDER=nebius
MODEL_NAME=moonshotai/Kimi-K2-Instruct
EDGAR_API_KEY=
SERPAPI_API_KEY=
```

### Task configuration
- The default task configuration is embedded in `src/config.py` as `TASK_CONFIG` and points to `data/public.csv`.

## Testing

Run A2A conformance tests against your agent.

```bash
# Install test dependencies
uv sync --extra test

# Start your agent (uv or docker; see above)

# Run tests against your running agent URL
uv run pytest --agent-url http://localhost:9009
```


