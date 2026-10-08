import asyncio
import ssl
import sys
from contextlib import AsyncExitStack
from uuid import UUID

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


from livekit.agents import (
    AgentSession,
    ConversationItemAddedEvent,
    FunctionToolsExecutedEvent,
    JobContext,
    JobProcess,
    RoomInputOptions,
    RoomOutputOptions,
    WorkerOptions,
    cli,
)
from livekit.agents.llm import Tool, Toolset
from livekit.agents.utils import http_context as lk_http_context
from livekit.agents.voice.room_io import TextInputEvent
from livekit.plugins import anthropic as lk_anthropic
from livekit.plugins import deepgram as lk_deepgram
from livekit.plugins import elevenlabs as lk_elevenlabs
from livekit.plugins import silero as lk_silero

from src.agent import ChatAgent
from src.api_client import open_agent_api_client
from src.config import get_anthropic_config, get_livekit_config, get_speech_config
from src.persistence import (
    ConversationPersistenceWorker,
    _conversation_item_to_row,
    _function_tools_executed_to_rows,
    hydrate_chat_context,
)
from src.tools import (
    build_invoices_function_tool,
    build_search_documents_function_tool,
    build_web_search_function_tool,
)


async def entrypoint(ctx: JobContext):
    session_id = UUID(ctx.job.metadata)
    await ctx.connect()
    shutdown_event = asyncio.Event()

    async def on_shutdown(_: str):
        shutdown_event.set()

    ctx.add_shutdown_callback(on_shutdown)

    async with AsyncExitStack() as stack:
        api = await stack.enter_async_context(open_agent_api_client(session_id))

        chat_ctx = hydrate_chat_context(await api.get_context())
        tools: list[Tool | Toolset] = [
            build_invoices_function_tool(api),
            build_web_search_function_tool(),
            build_search_documents_function_tool(api),
        ]

        agent = ChatAgent(api=api, chat_ctx=chat_ctx, tools=tools)
        await agent.refresh_documents()

        anthropic_config = get_anthropic_config()
        speech_config = get_speech_config()

        agent_session: AgentSession[None] = AgentSession(
            stt=lk_deepgram.STT(model=speech_config.DEEPGRAM_MODEL, api_key=speech_config.DEEPGRAM_API_KEY),
            llm=lk_anthropic.LLM(
                model=anthropic_config.ANTHROPIC_MODEL,
                api_key=anthropic_config.ANTHROPIC_API_KEY,
                max_tokens=anthropic_config.ANTHROPIC_MAX_TOKEN,
                _strict_tool_schema=False,
            ),
            tts=lk_elevenlabs.TTS(
                voice_id=speech_config.ELEVENLABS_VOICE_ID,
                model=speech_config.ELEVENLABS_MODEL,
                api_key=speech_config.ELEVENLABS_API_KEY,
            ),
            vad=ctx.proc.userdata["vad"],
        )

        worker = ConversationPersistenceWorker(api)

        @agent_session.on("conversation_item_added")
        def on_conversation_item_added(event: ConversationItemAddedEvent) -> None:
            row = _conversation_item_to_row(event.item)
            if row is not None:
                worker.enqueue(row)

        @agent_session.on("function_tools_executed")
        def on_function_tools_executed(event: FunctionToolsExecutedEvent) -> None:
            for row in _function_tools_executed_to_rows(event):
                worker.enqueue(row)

        stack.push_async_callback(worker.aclose)

        await agent_session.start(
            agent=agent,
            room=ctx.room,
            room_input_options=RoomInputOptions(text_enabled=True, audio_enabled=True, text_input_cb=text_only_reply_cb),
            room_output_options=RoomOutputOptions(transcription_enabled=True, audio_enabled=True),
        )

        await shutdown_event.wait()


# to answer text only
async def text_only_reply_cb(session: AgentSession, ev: TextInputEvent) -> None:
    async with session._claim_user_turn():
        if isinstance(session.current_agent, ChatAgent):
            await session.current_agent.refresh_documents()
        session.output.set_audio_enabled(False)
        try:
            await session.generate_reply(user_input=ev.text)
        finally:
            session.output.set_audio_enabled(True)


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = lk_silero.VAD.load()
    ssl_context = ssl.create_default_context()
    lk_http_context._create_ssl_context = lambda: ssl_context


def main() -> None:
    config = get_livekit_config()
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name=config.LIVEKIT_AGENT_NAME,
            ws_url=config.LIVEKIT_URL,
            api_key=config.LIVEKIT_API_KEY,
            api_secret=config.LIVEKIT_API_SECRET,
        )
    )


if __name__ == "__main__":
    main()
