LiveKit voice/text agent (STT -> Claude -> TTS), deployed to LiveKit Cloud. uv project, code in `src/`.

Commands: `uv sync`; `cp .env.example .env`; `uv run python -m src.entrypoint dev` (local, hot reload; `start` = prod, `download-files` = fetch VAD model); `uv run ruff check src`; `uv run mypy src`. Deploy and Docker check: `README.md`. Cloud secrets go in `.env.production` (`lk agent create|update-secrets --secrets-file .env.production`), never `.env`.

Boundary: never import anything from `animal/`. The agent has no DB/Stripe/MinIO env and talks to the API only over HTTP (`X-Agent-Token`, `${ANIMAL_API_URL}/api/v1/internal/agent/sessions/{id}/...`).

Contract: this side is `src/api_client.py` + `src/api_models.py`; the API side is `animal/app/routers/v1/agent_internal_router.py` + `animal/app/schemas/agent.py`. Change both together.

Local dev: `LIVEKIT_AGENT_NAME=animal-chat-agent-dev` in BOTH `animal/.env` and `animal-agent/.env`, otherwise jobs split between the cloud and the local agent. On Windows use `PYTHONUTF8=1` if logs crash with `UnicodeEncodeError`. Full-stack guide: `../README.md`.
