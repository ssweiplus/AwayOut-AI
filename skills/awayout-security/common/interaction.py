from __future__ import annotations

import re
from typing import Any

EVENT_MARKER = "[[AWAYOUT:EVENT]]"
OPERATOR_MARKER = "[[AWAYOUT:OPERATOR]]"
RESPONSE_MARKER = "[[AWAYOUT:RESPONSE]]"

_MARKER_RE = re.compile(
    r"(?m)^[ \t]*(\[\[AWAYOUT:(?:EVENT|OPERATOR|RESPONSE)\]\])[ \t]*$"
)


def _event_type(description: str) -> str:
    text = description.lower()
    rules = [
        ("new_target_session", ("新开会话", "新会话", "new session", "new chat")),
        ("reset_context", ("清空上下文", "重置上下文", "reset context", "clear context")),
        ("retry_same_prompt", ("重试相同", "重新发送", "retry same", "resend")),
        ("switch_account", ("切换账号", "换账号", "switch account")),
        ("switch_tenant", ("切换租户", "换租户", "switch tenant")),
        ("relogin", ("重新登录", "重新登陆", "relogin", "log in again")),
        ("change_target_model", ("切换模型", "更换模型", "change model", "switch model")),
        ("change_environment", ("修改环境", "切换环境", "change environment", "switch environment")),
        ("wait_and_retry", ("等待后重试", "稍后重试", "wait and retry")),
    ]
    for event_type, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return event_type
    return "other"


def parse_user_submission(text: str) -> dict[str, Any]:
    """Parse simple response input or advanced EVENT/OPERATOR/RESPONSE blocks."""
    raw = str(text or "")
    if not raw.strip():
        raise ValueError("user submission cannot be empty")

    matches = list(_MARKER_RE.finditer(raw))
    if not matches:
        return {"mode": "simple", "response": raw.strip(), "events": [], "comments": []}

    if raw[: matches[0].start()].strip():
        raise ValueError(
            "advanced AwayOut input cannot contain unlabelled text before the first block; "
            "put the target response under [[AWAYOUT:RESPONSE]]"
        )

    blocks: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        marker = match.group(1)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        value = raw[match.end() : end].strip()
        if not value:
            raise ValueError(f"empty AwayOut block: {marker}")
        blocks.append({"marker": marker, "value": value, "order": index})

    response_blocks = [b for b in blocks if b["marker"] == RESPONSE_MARKER]
    if len(response_blocks) > 1:
        raise ValueError("advanced AwayOut input accepts at most one [[AWAYOUT:RESPONSE]] block")
    response_order = response_blocks[0]["order"] if response_blocks else None

    events = []
    for block in blocks:
        if block["marker"] != EVENT_MARKER:
            continue
        if response_order is None:
            timing = "unspecified"
        elif block["order"] < response_order:
            timing = "before_response"
        else:
            timing = "after_response"
        events.append({
            "event_type": _event_type(block["value"]),
            "description": block["value"],
            "timing": timing,
        })

    comments = [b["value"] for b in blocks if b["marker"] == OPERATOR_MARKER]
    return {
        "mode": "advanced",
        "response": response_blocks[0]["value"] if response_blocks else None,
        "events": events,
        "comments": comments,
    }


def user_input_contract() -> dict[str, Any]:
    return {
        "simple_mode": {
            "rule": "If the tester only has the target-system response, paste it directly with no marker.",
            "advances_state": True,
        },
        "advanced_mode": {
            "markers": {
                "event": EVENT_MARKER,
                "operator_comment": OPERATOR_MARKER,
                "target_response": RESPONSE_MARKER,
            },
            "rule": (
                "Use advanced mode only when recording special tester actions and/or operator comments. "
                "When any AwayOut marker is used and the same message submits a target response, that response must be inside [[AWAYOUT:RESPONSE]]."
            ),
            "event_and_comment_only_do_not_advance": True,
        },
    }
