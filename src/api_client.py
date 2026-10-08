from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.api_models import (
    DocumentStatuses,
    InvoiceStatusValue,
    Role,
    SessionContext,
)
from src.config import get_agent_api_config
from src.logger import log

_RETRY_STATUSES = frozenset({502, 503, 504})


class AgentApiError(Exception):
    """Agent internal API call failed."""


class _RetryableAgentApiError(AgentApiError):
    """Transient failure (connect error, 502/503/504) that is safe to retry."""


class AgentApiClient:
    def __init__(self, http: httpx.AsyncClient, session_id: UUID) -> None:
        self._http = http
        self._session_id = session_id

    @property
    def session_id(self) -> UUID:
        return self._session_id

    @retry(
        retry=retry_if_exception_type(_RetryableAgentApiError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=0.5, max=4),
        reraise=True,
    )
    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = await self._http.request(method, path, **kwargs)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            log.warning("agent_api_connect_error", path=path, session_id=str(self._session_id), error=repr(exc))
            raise _RetryableAgentApiError(f"{method} {path} failed: {exc!r}") from exc
        except (httpx.HTTPError, httpx.InvalidURL, httpx.CookieConflict) as exc:
            raise AgentApiError(f"{method} {path} failed: {exc!r}") from exc

        if response.status_code >= 400:
            message = f"{method} {path} returned {response.status_code}: {response.text}"
            if response.status_code in _RETRY_STATUSES:
                log.warning("agent_api_retryable_status", path=path, status_code=response.status_code)
                raise _RetryableAgentApiError(message)
            raise AgentApiError(message)
        return response

    @staticmethod
    def _parse[T: BaseModel](response: httpx.Response, path: str, model: type[T]) -> T:
        try:
            return model.model_validate(response.json())
        except ValueError as exc:
            raise AgentApiError(f"{response.request.method} {path} returned invalid body: {exc!r}") from exc

    async def get_context(self) -> SessionContext:
        response = await self._request("GET", "/context")
        return self._parse(response, "/context", SessionContext)

    async def create_message(self, role: Role, content: Any, occurred_at: datetime) -> None:
        await self._request(
            "POST",
            "/messages",
            json={"role": role, "content": content, "occurred_at": occurred_at.isoformat()},
        )

    async def get_document_statuses(self) -> DocumentStatuses:
        response = await self._request("GET", "/documents/statuses")
        return self._parse(response, "/documents/statuses", DocumentStatuses)

    async def search_documents(self, query: str, top_k: int) -> str:
        response = await self._request("POST", "/documents/search", json={"query": query, "top_k": top_k})
        return response.text

    async def get_invoices(
        self,
        start_date: date | None,
        end_date: date | None,
        status: InvoiceStatusValue | None,
    ) -> str:
        params: dict[str, str] = {}
        if start_date is not None:
            params["start_date"] = start_date.isoformat()
        if end_date is not None:
            params["end_date"] = end_date.isoformat()
        if status is not None:
            params["status"] = status
        response = await self._request("GET", "/invoices", params=params)
        return response.text


@asynccontextmanager
async def open_agent_api_client(session_id: UUID) -> AsyncIterator[AgentApiClient]:
    config = get_agent_api_config()
    http = httpx.AsyncClient(
        base_url=f"{config.ANIMAL_API_URL.rstrip('/')}/api/v1/internal/agent/sessions/{session_id}",
        headers={"X-Agent-Token": config.AGENT_SERVICE_TOKEN},
        timeout=httpx.Timeout(config.AGENT_API_TIMEOUT_SECONDS, connect=5.0),
    )
    try:
        yield AgentApiClient(http, session_id)
    finally:
        await http.aclose()
