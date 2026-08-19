from __future__ import annotations

import re
from typing import Any

EVENT_MARKER = "[[AWAYOUT:EVENT]]"
OPERATOR_MARKER = "[[AWAYOUT:OPERATOR]]"
RESPONSE_MARKER = "[[AWAYOUT:RESPONSE]]"

_MARKERS = (EVENT_MARKER, OPERATOR_MARKER, RESPONSE_MARKER)
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
    """Parse simple target-response input or advanced multi-block input.

    Simple mode: no AwayOut markers => entire message is the target response.
    Advanced mode: one or more explicit EVENT / OPERATOR / RESPONSE blocks.
    """
    raw = str(text or "")
    if not raw.strip():
        raise ValueError("user submission cannot be empty")

    matches = list(_MARKER_RE.finditer(raw))
    if not matches:
        return {
            "mode": "simple",
            "response": raw.strip(),
            "events": [],
            "comments": [],
        }

    preamble = raw[: matches[0].start()].strip()
    if preamble:
        raise ValueError(
            "advanced AwayOut input cannot contain unlabelled text before the first block; "
            "put the target response under [[AWAYOUT:RESPONSE]]"
        )

    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        marker = match.group(1)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        value = raw[match.end() : end].strip()
        if not value:
            raise ValueError(f"empty AwayOut block: {marker}")
        blocks.append((marker, value))

    responses = [value for marker, value in blocks if marker == RESPONSE_MARKER]
    if len(responses) > 1:
        raise ValueError("advanced AwayOut input accepts at most one [[AWAYOUT:RESPONSE]] block")

    events = [
        {
            "event_type": _event_type(value),
            "description": value,
            "timing": "before_response" if responses else "unspecified",
        }
        for marker, value in blocks
        if marker == EVENT_MARKER
    ]
    comments = [value for marker, value in blocks if marker == OPERATOR_MARKER]

    return {
        "mode": "advanced",
        "response": responses[0] if responses else None,
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
                "Use advanced mode only when recording a special tester action and/or operator comment together with the response. "
                "When any AwayOut marker is used, the target response must be inside [[AWAYOUT:RESPONSE]]."
            ),
            "event_and_comment_only_do_not_advance": True,
        },
    }
