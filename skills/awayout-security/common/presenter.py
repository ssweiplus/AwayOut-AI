from __future__ import annotations

from typing import Any


OPERATOR_MARKER = "[[AWAYOUT:OPERATOR]]"


def _text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _fenced_text(value: str) -> str:
    fence = "````" if "```" in value else "```"
    return f"{fence}text\n{value}\n{fence}"


def _quote_lines(value: str) -> list[str]:
    return [f"> {line}" if line else ">" for line in value.splitlines()]


def _operator_section() -> list[str]:
    return [
        "### 人工意见（可选）",
        "如需补充人工判断，请单独发送一条消息，并以这一行开头：",
        "",
        _fenced_text(OPERATOR_MARKER + "\n<你的意见>"),
        "",
        "人工意见不会被当作目标系统响应，也不会推进当前步骤。",
    ]


def _current_feedback(lines: list[str], latest_feedback: dict | None) -> str:
    feedback_text = _text((latest_feedback or {}).get("text"))
    lines.extend(["", "### 当前人工意见"])
    if feedback_text:
        lines.extend(_quote_lines(feedback_text))
    else:
        lines.append("暂无。")
    return feedback_text


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


def render_pair_target_interaction(action: dict, latest_feedback: dict | None = None) -> dict:
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

    feedback_text = _current_feedback(lines, latest_feedback)

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
        "3. 评分、策略决策和下一轮生成由 AwayOut/Agent 内部完成，不需要你执行脚本。",
        "",
    ])
    lines.extend(_operator_section())

    return {
        "format": "markdown",
        "must_show_verbatim": True,
        "copy_target": "prompt_block_only",
        "prompt": prompt,
        "strategy": strategy,
        "iteration": iteration,
        "max_iterations": maximum,
        "operator_marker": OPERATOR_MARKER,
        "latest_feedback": feedback_text or None,
        "rendered_text": "\n".join(lines),
    }


def render_tap_branch_interaction(action: dict, latest_feedback: dict | None = None) -> dict:
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

    feedback_text = _current_feedback(lines, latest_feedback)

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
        "2. 将这一次的目标系统实际响应直接粘贴回来即可。",
        "3. 不需要填写 JSON、node_id，也不需要执行评分/剪枝脚本。",
        "4. 当前深度响应收集完成后，AwayOut/Agent 会内部评分、剪枝并生成下一步，再一次性展示。",
        "",
    ])
    lines.extend(_operator_section())

    return {
        "format": "markdown",
        "must_show_verbatim": True,
        "copy_target": "prompt_block_only",
        "input_mode": "single_plain_text_response",
        "node_id": node_id,
        "branch_index": index,
        "branch_total": total,
        "depth": depth,
        "max_depth": max_depth,
        "prompt": prompt,
        "operator_marker": OPERATOR_MARKER,
        "latest_feedback": feedback_text or None,
        "rendered_text": "\n".join(lines),
    }


def render_drattack_strategy_interaction(action: dict, latest_feedback: dict | None = None) -> dict:
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
    feedback_text = _current_feedback(lines, latest_feedback)

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
        "2. 将这一次的目标系统实际响应直接粘贴回来即可。",
        "3. 不需要填写 JSON，也不需要执行评分脚本；所有策略完成后统一评分并一次性展示结果。",
        "",
    ])
    lines.extend(_operator_section())

    return {
        "format": "markdown",
        "must_show_verbatim": True,
        "copy_target": "prompt_block_only",
        "input_mode": "single_plain_text_response",
        "strategy": strategy,
        "strategy_index": index,
        "strategy_total": total,
        "prompt": prompt,
        "operator_marker": OPERATOR_MARKER,
        "latest_feedback": feedback_text or None,
        "rendered_text": "\n".join(lines),
    }


def render_final_result(action: dict) -> dict:
    algorithm = _text(action.get("algorithm")) or "AwayOut"
    summary = action.get("summary") if isinstance(action.get("summary"), dict) else {}
    stop_reason = _text(action.get("stop_reason") or summary.get("stop_reason"))
    success = bool(summary.get("success"))

    lines = [
        f"## {algorithm} 测试结果",
        "",
        f"- 结果：{'达到成功条件' if success else '未达到成功条件'}",
    ]
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

    return {
        "format": "markdown",
        "must_show_verbatim": True,
        "rendered_text": "\n".join(lines),
    }
