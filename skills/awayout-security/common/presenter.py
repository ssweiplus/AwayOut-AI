from __future__ import annotations

from typing import Any

from common.interaction import EVENT_MARKER, OPERATOR_MARKER, RESPONSE_MARKER


def _text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _fenced_text(value: str) -> str:
    fence = "````" if "```" in value else "```"
    return f"{fence}text\n{value}\n{fence}"


def _quote_lines(value: str) -> list[str]:
    return [f"> {line}" if line else ">" for line in value.splitlines()]


def _current_operator_context(
    lines: list[str],
    latest_feedback: dict | None,
    latest_event: dict | None,
) -> tuple[str, str]:
    feedback_text = _text((latest_feedback or {}).get("text"))
    event_text = _text((latest_event or {}).get("description"))
    lines.extend(["", "### 本轮已记录的人工信息"])
    if not feedback_text and not event_text:
        lines.append("暂无。")
        return "", ""
    if event_text:
        event_type = _text((latest_event or {}).get("event_type")) or "other"
        lines.append(f"- 操作：`{event_type}` — {event_text}")
    if feedback_text:
        lines.append("- 意见：")
        lines.extend(_quote_lines(feedback_text))
    return feedback_text, event_text


def _tester_input_section() -> list[str]:
    return [
        "### 你应该怎么回复",
        "",
        "**通常情况：直接粘贴目标系统的完整响应即可，不需要任何标签。**",
        "",
        "如果本轮还有特殊人工操作或人工判断，可以和目标响应一起发送，使用下面的扩展格式：",
        "",
        _fenced_text(
            f"{EVENT_MARKER}\n新开会话\n\n"
            f"{OPERATOR_MARKER}\n我怀疑新会话影响了这次结果\n\n"
            f"{RESPONSE_MARKER}\n<这里粘贴目标系统的完整响应>"
        ),
        "",
        "扩展格式中三个区块都按需填写：",
        f"- `{EVENT_MARKER}`：记录你实际做了什么，例如新开会话、切换账号、清空上下文；可省略。",
        f"- `{OPERATOR_MARKER}`：记录你的判断、观察或给 Agent 的建议；可省略。",
        f"- `{RESPONSE_MARKER}`：目标系统真实响应。**只要使用了任意 AwayOut 标签并且本次要提交响应，就必须放在这个区块。**",
        "",
        "如果只发送操作/意见而没有响应，本轮不会推进；之后仍可继续提交目标响应。",
    ]


def _transition_summary(lines: list[str], action: dict) -> None:
    summary = action.get("transition_summary") if isinstance(action.get("transition_summary"), dict) else {}
    if not summary:
        return
    lines.extend(["", "### 上一步结果"])
    title = _text(summary.get("title"))
    if title:
        lines.append(f"- {title}")
    score = summary.get("score")
    if score is not None:
        lines.append(f"- 评分：**{int(score)}/10**")
    reason = _text(summary.get("reason"))
    if reason:
        lines.append(f"- 依据：{reason}")
    remaining = _text(summary.get("remaining_gap"))
    if remaining:
        lines.append(f"- 尚缺：{remaining}")
    items = summary.get("items") if isinstance(summary.get("items"), list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        label = _text(item.get("label")) or "result"
        item_score = item.get("score")
        item_reason = _text(item.get("reason"))
        text = f"- {label}"
        if item_score is not None:
            text += f"：{int(item_score)}/10"
        if item_reason:
            text += f" — {item_reason}"
        lines.append(text)


def render_pair_target_interaction(
    action: dict,
    latest_feedback: dict | None = None,
    latest_event: dict | None = None,
) -> dict:
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
    lines = [title]
    _transition_summary(lines, action)
    lines.extend(["", "### 本轮策略", f"- 策略：`{strategy}`"])
    if description:
        lines.append(f"- 说明：{description}")
    feedback_text, event_text = _current_operator_context(lines, latest_feedback, latest_event)

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
        "### 测试步骤",
        "1. 只复制上面的 Prompt 代码块内容到目标系统。",
        "2. 获取目标系统响应后，按下方说明回复本对话。",
        "3. 评分、策略决策和下一轮生成由 AwayOut/Agent 内部完成，不需要你执行脚本。",
        "",
    ])
    lines.extend(_tester_input_section())

    return {
        "format": "markdown",
        "must_show_verbatim": True,
        "copy_target": "prompt_block_only",
        "input_mode": "simple_or_advanced_blocks",
        "prompt": prompt,
        "strategy": strategy,
        "iteration": iteration,
        "max_iterations": maximum,
        "markers": {"event": EVENT_MARKER, "operator": OPERATOR_MARKER, "response": RESPONSE_MARKER},
        "latest_feedback": feedback_text or None,
        "latest_event": event_text or None,
        "rendered_text": "\n".join(lines),
    }


def render_tap_branch_interaction(
    action: dict,
    latest_feedback: dict | None = None,
    latest_event: dict | None = None,
) -> dict:
    current = action.get("current_branch") if isinstance(action.get("current_branch"), dict) else {}
    progress = action.get("progress") if isinstance(action.get("progress"), dict) else {}
    index = int(current.get("index") or 0)
    total = int(current.get("total") or 0)
    depth = int(current.get("depth") or progress.get("depth") or 0)
    max_depth = int(progress.get("max_depth") or 0)
    node_id = _text(current.get("node_id")) or "unknown"
    improvement = _text(current.get("improvement"))
    prompt = _text(current.get("prompt"))
    if not prompt:
        raise ValueError("TAP branch interaction template requires a non-empty prompt")

    title = f"## TAP 深度 {depth}/{max_depth} · 分支测试 {index}/{total}" if max_depth else f"## TAP 深度 {depth} · 分支测试 {index}/{total}"
    lines = [title]
    _transition_summary(lines, action)
    lines.extend([
        "",
        "### 当前分支",
        f"- 分支：`{node_id}`",
        "- 说明：本次只测试这一条；提交响应后会自动进入当前深度的下一个存活分支。",
    ])
    if improvement:
        lines.append(f"- 变异方向：{improvement}")
    feedback_text, event_text = _current_operator_context(lines, latest_feedback, latest_event)

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
        "### 测试步骤",
        "1. 只复制上面的 Prompt 代码块内容到目标系统。",
        "2. 获取目标系统响应后，按下方说明回复本对话。",
        "3. 不需要填写 JSON、node_id，也不需要执行评分/剪枝脚本。",
        "4. 当前深度响应收集完成后，AwayOut/Agent 会内部评分、剪枝并生成下一步，再一次性展示。",
        "",
    ])
    lines.extend(_tester_input_section())

    return {
        "format": "markdown",
        "must_show_verbatim": True,
        "copy_target": "prompt_block_only",
        "input_mode": "simple_or_advanced_blocks",
        "node_id": node_id,
        "branch_index": index,
        "branch_total": total,
        "depth": depth,
        "max_depth": max_depth,
        "prompt": prompt,
        "markers": {"event": EVENT_MARKER, "operator": OPERATOR_MARKER, "response": RESPONSE_MARKER},
        "latest_feedback": feedback_text or None,
        "latest_event": event_text or None,
        "rendered_text": "\n".join(lines),
    }


def render_drattack_strategy_interaction(
    action: dict,
    latest_feedback: dict | None = None,
    latest_event: dict | None = None,
) -> dict:
    current = action.get("current_strategy") if isinstance(action.get("current_strategy"), dict) else {}
    index = int(current.get("index") or 0)
    total = int(current.get("total") or 0)
    strategy = _text(current.get("strategy")) or "unknown"
    prompt = _text(current.get("prompt"))
    if not prompt:
        raise ValueError("DrAttack strategy interaction template requires a non-empty prompt")

    title = f"## DrAttack 策略测试 {index}/{total}" if total else f"## DrAttack 策略测试 {index}"
    lines = [title]
    _transition_summary(lines, action)
    lines.extend([
        "",
        "### 当前策略",
        f"- 策略：`{strategy}`",
        "- 说明：本次只测试这一条；提交响应后会自动进入下一个策略。",
    ])
    feedback_text, event_text = _current_operator_context(lines, latest_feedback, latest_event)

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
        "### 测试步骤",
        "1. 只复制上面的 Prompt 代码块内容到目标系统。",
        "2. 获取目标系统响应后，按下方说明回复本对话。",
        "3. 不需要填写 JSON，也不需要执行评分脚本；所有策略完成后统一评分并一次性展示结果。",
        "",
    ])
    lines.extend(_tester_input_section())

    return {
        "format": "markdown",
        "must_show_verbatim": True,
        "copy_target": "prompt_block_only",
        "input_mode": "simple_or_advanced_blocks",
        "strategy": strategy,
        "strategy_index": index,
        "strategy_total": total,
        "prompt": prompt,
        "markers": {"event": EVENT_MARKER, "operator": OPERATOR_MARKER, "response": RESPONSE_MARKER},
        "latest_feedback": feedback_text or None,
        "latest_event": event_text or None,
        "rendered_text": "\n".join(lines),
    }


def render_final_result(action: dict) -> dict:
    algorithm = _text(action.get("algorithm")) or "AwayOut"
    summary = action.get("summary") if isinstance(action.get("summary"), dict) else {}
    stop_reason = _text(action.get("stop_reason") or summary.get("stop_reason"))
    success = bool(summary.get("success"))

    lines = [f"## {algorithm} 测试结果", "", f"- 结果：{'达到成功条件' if success else '未达到成功条件'}"]
    if stop_reason:
        lines.append(f"- 停止原因：`{stop_reason}`")

    best = summary.get("best_node") if isinstance(summary.get("best_node"), dict) else None
    if best is None and isinstance(summary.get("best_strategy"), dict):
        best = summary.get("best_strategy")
    if isinstance(best, dict):
        lines.extend(["", "### 最佳结果"])
        label = _text(best.get("strategy") or best.get("node_id"))
        if label:
            lines.append(f"- 项目：`{label}`")
        if best.get("score") is not None:
            lines.append(f"- 评分：**{int(best['score'])}/10**")
        reason = _text(best.get("reason"))
        if reason:
            lines.append(f"- 评分依据：{reason}")

    tree = _text(summary.get("tree"))
    if tree:
        lines.extend(["", "### 路径摘要", "", _fenced_text(tree)])

    return {"format": "markdown", "must_show_verbatim": True, "rendered_text": "\n".join(lines)}
