FROM ghcr.io/astral-sh/uv:python3.13-bookworm

RUN adduser agent
USER agent
WORKDIR /home/agent

COPY pyproject.toml uv.lock README.md ./
COPY src src

RUN \
    --mount=type=cache,target=/home/agent/.cache/uv,uid=1000 \
    uv sync --locked

# Expose A2A and extra MCP port
EXPOSE 9009 9020

ENTRYPOINT ["uv", "run", "src/server.py"]

CMD ["--host", "0.0.0.0"]
