import json
from typing import Any, Literal

from livekit.agents import FunctionToolsExecutedEvent, llm

from src.api_models import Role, SessionContext
from src.prompts import ASSISTANT_SUMMARY_TEMPLATE, SUMMARY_TEMPLATE


def _content_blocks_to_chat_items(role: Role, content: Any) -> list[llm.ChatItem]:
    if role == "tool":
        return [
            llm.FunctionCallOutput(
                call_id=block["tool_use_id"],
                output=block["content"] if isinstance(block["content"], str) else json.dumps(block["content"]),
                is_error=False,
            )
            for block in content
        ]

    chat_role: Literal["user", "assistant"] = "user" if role == "user" else "assistant"

    if isinstance(content, str):
        return [llm.ChatMessage(role=chat_role, content=[content])] if content else []

    items: list[llm.ChatItem] = []
    text_parts: list[str] = []
    for block in content:
        if block["type"] == "text":
            text_parts.append(block["text"])
        elif block["type"] == "tool_use":
            if text_parts:
                items.append(llm.ChatMessage(role=chat_role, content=list(text_parts)))
                text_parts = []
            items.append(llm.FunctionCall(call_id=block["id"], name=block["name"], arguments=json.dumps(block["input"])))
        elif block["type"] == "file":
            text_parts.append(f"[file: {block.get('filename') or block['media_type']}]")
    if text_parts:
        items.append(llm.ChatMessage(role=chat_role, content=list(text_parts)))
    return items


def hydrate_chat_context(context: SessionContext) -> llm.ChatContext:
    items: list[llm.ChatItem] = []
    if context.summary:
        items.append(llm.ChatMessage(role="user", content=[SUMMARY_TEMPLATE.format(summary=context.summary)]))
        items.append(llm.ChatMessage(role="assistant", content=[ASSISTANT_SUMMARY_TEMPLATE]))

    for message in context.messages:
        items.extend(_content_blocks_to_chat_items(message.role, message.content))
    return llm.ChatContext(items=items)


def _conversation_item_to_row(item: Any) -> tuple[Role, Any] | None:
    if not isinstance(item, llm.ChatMessage) or item.role not in ("user", "assistant"):
        return None

    text = "".join(part for part in item.content if isinstance(part, str))
    if not text:
        return None

    if item.role == "user":
        return ("user", text)
    return ("assistant", [{"type": "text", "text": text}])


def _function_tools_executed_to_rows(event: FunctionToolsExecutedEvent) -> list[tuple[Role, Any]]:
    rows: list[tuple[Role, Any]] = []
    for call in event.function_calls:
        rows.append(("assistant", [{"type": "tool_use", "id": call.call_id, "name": call.name, "input": json.loads(call.arguments or "{}")}]))
    for output in event.function_call_outputs:
        rows.append(("tool", [{"type": "tool_result", "tool_use_id": output.call_id, "content": output.output}]))
    return rows
