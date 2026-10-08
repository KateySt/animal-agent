import asyncio
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from src.api_client import AgentApiClient, AgentApiError
from src.api_models import Role
from src.logger import log

_DRAIN_TIMEOUT_SECONDS = 10.0


class ConversationPersistenceWorker:
    def __init__(self, api: AgentApiClient) -> None:
        self._api = api
        self._queue: asyncio.Queue[tuple[Role, Any, datetime]] = asyncio.Queue(maxsize=256)
        self._consume_task = asyncio.create_task(self._consume(), name="persistence_consumer")

    def enqueue(self, row: tuple[Role, Any]) -> None:
        role, content = row
        item = (role, content, datetime.now(UTC))
        try:
            self._queue.put_nowait(item)
        except asyncio.QueueFull:
            log.warning("persistence_queue_full_dropping_oldest", session_id=str(self._api.session_id))
            self._queue.get_nowait()
            self._queue.task_done()
            self._queue.put_nowait(item)

    async def aclose(self) -> None:
        try:
            await asyncio.wait_for(self._queue.join(), timeout=_DRAIN_TIMEOUT_SECONDS)
        except TimeoutError:
            log.warning(
                "persistence_drain_timeout",
                session_id=str(self._api.session_id),
                undelivered_rows=self._queue.qsize(),
            )
        self._consume_task.cancel()
        with suppress(asyncio.CancelledError):
            await self._consume_task

    async def _consume(self) -> None:
        while True:
            role, content, occurred_at = await self._queue.get()
            try:
                await self._persist(role, content, occurred_at)
            finally:
                self._queue.task_done()

    async def _persist(self, role: Role, content: Any, occurred_at: datetime) -> None:
        try:
            await self._api.create_message(role, content, occurred_at)
        except AgentApiError:
            log.exception("persist_conversation_item_failed", role=role, session_id=str(self._api.session_id))
        except Exception:
            log.exception("persist_conversation_item_unexpected_error", role=role, session_id=str(self._api.session_id))
