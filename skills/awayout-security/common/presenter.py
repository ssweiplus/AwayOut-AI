from __future__ import annotations

from typing import Any


OPERATOR_MARKER = "[[AWAYOUT:OPERATOR]]"


def _text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _fenced_text(value: str) -> str:
    # Keep the copy target visually isolated. If the prompt itself contains a
    # triple-backtick fence, use a four-backtick outer fence instead.
    fence = "````" if "```" in value else "```"
    return f"{fence}text\n{value}\n{fence}"


def render_pair_target_interaction(action: dict) -> dict:
    """Render a PAIR WAIT_TARGET_RESPONSE payload for direct user display.

    The result intentionally separates metadata from the copyable prompt so a
    tester can copy only the prompt block without accidentally including
    strategy notes or operator guidance.
    """
    node = action.get("node") if isinstance(action.get("node"), dict) else {}
    progress = action.get("progress") if isinstance(action.get("progress"), dict) else {}
    handoff = action.get("handoff") if isinstance(action.get("handoff"), dict) else {}
    guidance = handoff.get("strategy_guidance") if isinstance(handoff.get("strategy_guidance"), dict) else {}

    iteration = int(node.get("iteration") or progress.get("attempts_created") or 0)
    maximum = int(progress.get("max_iterations") or 0)
    strategy = _text(node.get("strategy") or action.get("strategy") or guidance.get("id")) or "unknown"
    description = _text(guidance.get("description"))
    prompt = _text(node.get("prompt"))

    if not prompt:
        raise ValueError("PAIR target interaction template requires a non-empty prompt")

    title = f"## PAIR 第 {iteration}/{maximum} 轮" if maximum else f"## PAIR 第 {iteration} 轮"
    lines = [
        title,
        "",
        "### 本轮策略",
        f"- 策略：`{strategy}`",
    ]
    if description:
        lines.append(f"- 说明：{description}")

    lines.extend([
        "",
        "---",
        "",
        "### 请只复制下面的 Prompt",
        "",
        _fenced_text(prompt),
        "",
        "---",
        "",
        "### 下一步",
        "1. 只复制上面的 Prompt 代码块内容到目标系统。",
        "2. 将目标系统的实际响应完整粘贴回来。",
        "3. 目标响应不要添加人工分析、评价或说明。",
        "",
        "### 人工意见（可选）",
        "如需补充人工判断，请单独发送一条消息，并以这一行开头：",
        "",
        _fenced_text(OPERATOR_MARKER + "\n<你的意见>"),
        "",
        "人工意见不会被当作目标系统响应，也不会推进当前轮次。",
    ])

    return {
        "format": "markdown",
        "must_show_verbatim": True,
        "copy_target": "prompt_block_only",
        "prompt": prompt,
        "strategy": strategy,
        "iteration": iteration,
        "max_iterations": maximum,
        "operator_marker": OPERATOR_MARKER,
        "rendered_text": "\n".join(lines),
    }
