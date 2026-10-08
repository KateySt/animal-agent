FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src

RUN LIVEKIT_URL=wss://build.invalid LIVEKIT_API_KEY=build LIVEKIT_API_SECRET=build \
    uv run --no-sync python -m src.entrypoint download-files

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "--no-sync", "python", "-m", "src.entrypoint", "start"]
