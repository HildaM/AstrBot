import json
from typing import Any

from astrbot import logger
from astrbot.core.conversation_mgr import ConversationManager
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.provider.entities import ProviderRequest


def _build_structured_summary(
    summary_note: str,
    cron_meta: dict[str, Any] | None = None,
) -> str:
    """Build a structured summary that preserves task execution context.

    For cron-triggered tasks, this includes structured metadata so future
    agent runs can recall what was done, when, and by which cron job.
    """
    if not cron_meta:
        return summary_note

    timestamp = cron_meta.get("run_started_at", "unknown")
    job_name = cron_meta.get("name") or cron_meta.get("id", "unknown")
    job_desc = cron_meta.get("description", "")

    structured = (
        f"[Scheduled Task Execution Record]\n"
        f"- Task: {job_name}\n"
        f"- Description: {job_desc}\n"
        f"- Triggered at: {timestamp}\n"
        f"- Result: {summary_note}\n"
    )
    return structured


async def persist_agent_history(
    conversation_manager: ConversationManager,
    *,
    event: AstrMessageEvent,
    req: ProviderRequest,
    summary_note: str,
    cron_meta: dict[str, Any] | None = None,
) -> None:
    """Persist agent interaction into conversation history.

    Args:
        conversation_manager: The conversation manager instance.
        event: The message event associated with this agent run.
        req: The provider request containing conversation context.
        summary_note: A human-readable summary of what the agent did.
        cron_meta: Optional cron job metadata for structured recording.
            When provided, the history entry will include structured task
            execution details to improve cross-run memory recall.
    """
    if not req or not req.conversation:
        return

    history = []
    try:
        history = json.loads(req.conversation.history or "[]")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse conversation history: %s", exc)

    structured_summary = _build_structured_summary(summary_note, cron_meta)

    history.append({"role": "user", "content": "Output your last task result below."})
    history.append({"role": "assistant", "content": structured_summary})
    await conversation_manager.update_conversation(
        event.unified_msg_origin,
        req.conversation.cid,
        history=history,
    )
