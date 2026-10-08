import asyncio

from livekit.agents import Agent, llm
from livekit.agents.voice.generation import update_instructions

from src.api_client import AgentApiClient, AgentApiError
from src.logger import log
from src.prompts import CHAT_DOCUMENTS_TEMPLATE, SYSTEM_PROMPT

_REFRESH_TIMEOUT_SECONDS = 3.0


class ChatAgent(Agent):
    def __init__(self, *, api: AgentApiClient, **kwargs) -> None:
        super().__init__(instructions=SYSTEM_PROMPT, **kwargs)
        self._api = api

    async def refresh_documents(self, turn_ctx: llm.ChatContext | None = None) -> None:
        try:
            instructions = await asyncio.wait_for(self._build_instructions(), timeout=_REFRESH_TIMEOUT_SECONDS)
        except (AgentApiError, TimeoutError) as exc:
            log.warning("refresh_documents_failed_keeping_instructions", error=repr(exc))
            return
        if instructions != self.instructions:
            await self.update_instructions(instructions)
        if turn_ctx is not None:
            update_instructions(turn_ctx, instructions=instructions, add_if_missing=True)

    async def on_user_turn_completed(self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage) -> None:
        await self.refresh_documents(turn_ctx)

    async def _build_instructions(self) -> str:
        statuses = await self._api.get_document_statuses()
        documents = CHAT_DOCUMENTS_TEMPLATE.format(
            ready=", ".join(statuses.ready_documents) or "none",
            processing=", ".join(statuses.processing_documents) or "none",
            failed=", ".join(statuses.failed_documents) or "none",
        )
        return f"{SYSTEM_PROMPT}\n\n{documents}"
