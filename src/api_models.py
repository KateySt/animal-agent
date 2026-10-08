from typing import Any, Literal

from pydantic import BaseModel

Role = Literal["user", "assistant", "tool"]
InvoiceStatusValue = Literal["pending", "processing", "paid", "cancelled"]


class ContextMessage(BaseModel):
    role: Role
    content: Any


class SessionContext(BaseModel):
    summary: str | None = None
    messages: list[ContextMessage]


class DocumentStatuses(BaseModel):
    ready_documents: list[str]
    processing_documents: list[str]
    failed_documents: list[str]
