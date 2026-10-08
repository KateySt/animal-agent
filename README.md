# animal-agent

LiveKit voice/text agent for the animal shelter chat: STT (Deepgram) -> Claude -> TTS (ElevenLabs), with
Exa web search. It runs in **LiveKit Cloud** and has no database access: it talks to the `animal` API
over HTTP only.

**Stack:** LiveKit Agents · Anthropic · Deepgram · ElevenLabs · Exa · uv · Python 3.12

> Running the whole system? See the [root README](../README.md).

## Setup

```bash
uv sync
cp .env.example .env     # Windows PowerShell: Copy-Item .env.example .env
```

Fill in `.env` for **local runs** (`.env.example` is the source of truth; blank numeric values must be filled or the line removed). `.env` is local only: `LIVEKIT_AGENT_NAME=animal-chat-agent-dev`, `ANIMAL_API_URL=http://localhost:8000`, `LIVEKIT_*` uncommented. Cloud secrets live in a separate `.env.production` (see Deploy).

| Variable | Notes |
|---|---|
| `LOG_LEVEL` | |
| `ANTHROPIC_API_KEY` `ANTHROPIC_MODEL` `ANTHROPIC_MAX_TOKEN` | LLM |
| `DEEPGRAM_API_KEY` `DEEPGRAM_MODEL` | STT |
| `ELEVENLABS_API_KEY` `ELEVENLABS_VOICE_ID` `ELEVENLABS_MODEL` | TTS |
| `EXA_API_KEY` | web search tool |
| `ANIMAL_API_URL` | API address: public URL in cloud, `http://localhost:8000` locally |
| `AGENT_SERVICE_TOKEN` | at least 32 chars; must equal `AGENT_SERVICE_TOKEN` in `animal/.env` (API answers 401 otherwise). Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `AGENT_API_TIMEOUT_SECONDS` | default 15 |
| `LIVEKIT_AGENT_NAME` | production `animal-chat-agent`, local `animal-chat-agent-dev` |
| `LIVEKIT_URL` `LIVEKIT_API_KEY` `LIVEKIT_API_SECRET` | local runs only; LiveKit Cloud injects them |

## Local run

```bash
uv run python -m src.entrypoint dev      # hot reload, verbose logs
```

Set `LIVEKIT_AGENT_NAME=animal-chat-agent-dev` in **both** `animal/.env` (the API dispatches by it) and
`animal-agent/.env`, otherwise jobs are split between the cloud and the local agent. Without a running
agent, sessions open but no reply ever arrives. On Windows set `PYTHONUTF8=1` if logs crash with
`UnicodeEncodeError`.

Quality: `uv run ruff check src` · `uv run mypy src`.

## Docker check

Image: `Dockerfile` (python:3.12-slim + uv, downloads the Silero VAD model at build,
`CMD uv run --no-sync python -m src.entrypoint start`).

```bash
docker build -t animal-agent .
docker run --rm --env-file .env -e ANIMAL_API_URL=http://host.docker.internal:8000 animal-agent
```

## Deploy to LiveKit Cloud

Create `.env.production` yourself (git- and docker-ignored; never commit it): copy `.env.example`, then set
`LIVEKIT_AGENT_NAME=animal-chat-agent`, `ANIMAL_API_URL=<public API URL>` and the real keys, and leave out every
`LIVEKIT_*` line (LiveKit Cloud injects them). Do not pass `.env` to `lk`: it would register the dev agent name,
point at localhost and upload `LIVEKIT_*` as secrets.

Run from `animal-agent/`:

```bash
lk cloud auth
lk agent create --secrets-file .env.production     # first time; writes livekit.toml (keep it in the repo)
lk agent deploy                         # updates
lk agent update-secrets --secrets-file .env.production
lk agent secrets                        # must list no DB_* / STRIPE_* / MINIO_*
lk agent status
lk agent logs
lk agent rollback
```

The API must be reachable from the internet (deployed URL; for tests `cloudflared tunnel --url http://localhost:8000`).

## Contract with the API

Base `${ANIMAL_API_URL}/api/v1/internal/agent/sessions/{session_id}`, header `X-Agent-Token: <AGENT_SERVICE_TOKEN>`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/context` | session context for the agent |
| POST | `/messages` | persist chat messages |
| GET | `/documents/statuses` | chat document statuses |
| POST | `/documents/search` | document search (book-rag, done by the API) |
| GET | `/invoices` | user invoices |

This side: `src/api_client.py` + `src/api_models.py`. The other side:
[`animal/app/routers/v1/agent_internal_router.py`](../animal/app/routers/v1/agent_internal_router.py) +
[`animal/app/schemas/agent.py`](../animal/app/schemas/agent.py). Change both together.
