from __future__ import annotations

from pathlib import Path
from typing import Any


def _text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _runtime(document: dict[str, Any]) -> dict[str, Any]:
    value = document.get("_runtime")
    return value if isinstance(value, dict) else {}


def _nodes(document: dict[str, Any]) -> list[dict[str, Any]]:
    algorithm = _text(document.get("algorithm")).upper()
    if algorithm in {"PAIR", "TAP"}:
        return [n for n in document.get("nodes", []) if isinstance(n, dict)]
    if algorithm in {"DRATTACK", "DR_ATTACK"}:
        return [n for n in document.get("strategy_nodes", []) if isinstance(n, dict)]
    return []


def _node_ref(document: dict[str, Any], node: dict[str, Any]) -> str:
    algorithm = _text(document.get("algorithm")).upper()
    if algorithm in {"PAIR", "TAP"}:
        return _text(node.get("node_id"))
    if algorithm in {"DRATTACK", "DR_ATTACK"}:
        return _text(node.get("strategy"))
    return ""


def _round_title(index: int) -> str:
    return f"round{index:02d}.md"


def _score(node: dict[str, Any]) -> int | None:
    value = node.get("score")
    return int(value) if value is not None else None


def _status(node: dict[str, Any], threshold: int) -> str:
    score = _score(node)
    if score is None:
        return "⏳ 未评分"
    return "✅ 成功" if score >= threshold else "❌ 未达标"


def _linked(runtime: dict[str, Any], key: str, ref: str) -> list[dict[str, Any]]:
    return [
        item for item in runtime.get(key, [])
        if isinstance(item, dict) and ref and _text(item.get("source_ref")) == ref
    ]


def _feedback_for_node(document: dict[str, Any], node: dict[str, Any]) -> list[dict[str, Any]]:
    return _linked(_runtime(document), "feedback", _node_ref(document, node))


def _events_for_node(document: dict[str, Any], node: dict[str, Any]) -> list[dict[str, Any]]:
    return _linked(_runtime(document), "operator_events", _node_ref(document, node))


def _session_items(runtime: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [item for item in runtime.get(key, []) if isinstance(item, dict)]


def _format_feedback(items: list[dict[str, Any]]) -> str:
    if not items:
        return "无"
    return "\n".join(
        f"- {item.get('created_at', '')}: {item.get('text', '')}"
        for item in items
    )


def _format_events(items: list[dict[str, Any]]) -> str:
    if not items:
        return "无"
    return "\n".join(
        f"- {item.get('created_at', '')} / {item.get('timing', 'unspecified')} / "
        f"`{item.get('event_type', 'other')}`：{item.get('description', '')}"
        for item in items
    )


def _round_markdown(document: dict[str, Any], node: dict[str, Any], index: int, total: int) -> str:
    threshold = int(document.get("threshold", 7))
    algorithm = _text(document.get("algorithm")).upper()
    strategy = _text(node.get("strategy")) or _text(node.get("improvement")) or "未记录"
    prompt = _text(node.get("prompt"))
    response = _text(node.get("response"))
    score = _score(node)
    reason = _text(node.get("reason")) or "尚未评分。"
    feedback = _feedback_for_node(document, node)
    events = _events_for_node(document, node)

    return f"""# Round {index}

[← SUMMARY](../SUMMARY.md) · [prompt-tree](../prompt-tree.md)

## 元数据
| 字段 | 值 |
|------|-----|
| 轮次 | {index}/{total} |
| 算法 | {algorithm} |
| 策略 | {strategy} |
| 评分 | {score if score is not None else '未评分'}/10 |
| 状态 | {_status(node, threshold)} |
| 特殊人工操作 | {'有' if events else '无'} |
| 操作员意见 | {'有' if feedback else '无'} |

## 测试者操作
{_format_events(events)}

## 操作员意见
{_format_feedback(feedback)}

## Prompt
```text
{prompt}
```

## 目标系统响应
```text
{response}
```

## 评分理由
{reason}

## 关联分析
- 与前几轮的关联：由 `ATTACK_PATTERN.md` / `strategy-evolution.md` 汇总。
- 对后续测试的影响：由 Working Memory、评分和本轮测试条件共同判断。
- 若本轮存在新开会话、切换账号、重置上下文等操作，评分变化不能默认完全归因于 Prompt 策略。
"""


def _turning_points(document: dict[str, Any], nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    threshold = int(document.get("threshold", 7))
    points: list[dict[str, Any]] = []
    previous_score: int | None = None
    previous_strategy = ""
    reached = False
    full = False
    for idx, node in enumerate(nodes, 1):
        score = _score(node)
        strategy = _text(node.get("strategy")) or _text(node.get("improvement"))
        events = _events_for_node(document, node)
        feedback = _feedback_for_node(document, node)
        kinds: list[str] = []
        if score is not None and score >= threshold and not reached:
            kinds.append("评分首次达标")
            reached = True
        if score == 10 and not full:
            kinds.append("评分首次满分")
            full = True
        if score is not None and previous_score is not None and abs(score - previous_score) >= 3:
            kinds.append("评分变化 ≥ 3")
        if previous_strategy and strategy and strategy != previous_strategy:
            kinds.append("策略重大切换")
        if events:
            kinds.append("测试条件发生变化")
        if feedback and score is not None and previous_score is not None and score != previous_score:
            kinds.append("操作员反馈可能影响结果")
        if kinds:
            points.append({
                "round": idx,
                "types": kinds,
                "from_score": previous_score,
                "to_score": score,
                "strategy": strategy,
                "reason": _text(node.get("reason")),
                "events": events,
            })
        if score is not None:
            previous_score = score
        if strategy:
            previous_strategy = strategy
    return points


def _key_findings(runtime: dict[str, Any]) -> str:
    memory = runtime.get("working_memory") if isinstance(runtime.get("working_memory"), dict) else {}
    items = [
        item for item in memory.get("items", [])
        if isinstance(item, dict)
        and item.get("status") not in {"stale", "superseded"}
        and _text(item.get("content"))
    ]
    items.sort(
        key=lambda item: (
            int(item.get("relevance_to_objective", 0)),
            int(item.get("importance", 0)),
            float(item.get("confidence", 0)),
        ),
        reverse=True,
    )
    selected = items[:5]
    if not selected:
        return "1. 暂无已沉淀的高置信关键发现。"
    return "\n".join(
        f"{idx}. {_text(item.get('content'))}"
        + (f"（来源：{_text(item.get('source_ref'))}）" if _text(item.get('source_ref')) else "")
        for idx, item in enumerate(selected, 1)
    )


def _summary(document: dict[str, Any], nodes: list[dict[str, Any]]) -> str:
    runtime = _runtime(document)
    scores = [_score(n) for n in nodes if _score(n) is not None]
    best = max(scores) if scores else None
    threshold = int(document.get("threshold", 7))
    success_count = sum(1 for s in scores if s is not None and s >= threshold)
    state = _text(document.get("state"))
    result = "成功" if success_count else ("进行中" if state != "DONE" else "失败")
    metadata = runtime.get("metadata") if isinstance(runtime.get("metadata"), dict) else {}
    started = _text(runtime.get("created_at")) or "未记录"
    updated = _text(runtime.get("updated_at")) or "未记录"
    config_fields = []
    for key in ("max_iterations", "threshold", "stop_policy", "branch_factor", "max_depth", "width", "top_k_synonyms", "strategies"):
        if key in document:
            config_fields.append(f"{key}={document.get(key)}")
    links = "\n".join(f"- [Round {i}](RESPONSES/{_round_title(i)})" for i in range(1, len(nodes) + 1)) or "- 暂无轮次"
    feedback_count = len(_session_items(runtime, "feedback"))
    event_count = len(_session_items(runtime, "operator_events"))

    return f"""# 测试总览

## 测试元数据
- 会话 ID：{document.get('session_id', '')}
- 测试目标：{document.get('objective', '')}
- 目标系统：{metadata.get('target_system', '未填写')}
- 算法：{document.get('algorithm', '')}
- 配置：{'; '.join(config_fields) if config_fields else '未记录'}
- 测试时间：{started} ~ {updated}
- 测试时长：由时间戳计算；若中断则以最后更新时间为止
- 最佳评分：{best if best is not None else '未评分'}
- 成功尝试数：{success_count}
- 特殊人工操作数：{event_count}
- 操作员意见数：{feedback_count}
- 最终状态：{state or '未记录'}

## 测试结果
- 状态：{result}
- 评分趋势：{scores}

## 关键发现（3-5条）
{_key_findings(runtime)}

## 防御建议（2-4条）
在测试完成后基于真实路径填写；不要脱离记录猜测。

## 归档导航
- [攻击链路与策略分析](ATTACK_PATTERN.md)
- [关键转折点](TURNING_POINTS.md)
- [完整决策树](prompt-tree.md)
- [策略演化](strategy-evolution.md)

### 完整轮次
{links}
"""


def _turning_markdown(document: dict[str, Any], nodes: list[dict[str, Any]]) -> str:
    points = _turning_points(document, nodes)
    lines = ["# 关键转折点", ""]
    if not points:
        lines.append("当前尚未命中自动判定的关键转折点。")
        return "\n".join(lines) + "\n"
    for point in points:
        rnd = point["round"]
        lines.extend([
            f"## 转折点：Round {rnd} — {' / '.join(point['types'])}",
            "",
            f"**评分变化：** {point['from_score'] if point['from_score'] is not None else 'N/A'} → {point['to_score'] if point['to_score'] is not None else 'N/A'}",
            "",
            "**前几轮的困境：**",
            "以此前轮次的完整响应与评分理由为准。",
            "",
            "**突破方式：**",
            f"策略/方向：{point['strategy'] or '未记录'}",
        ])
        if point["events"]:
            lines.append("测试条件变化：" + "；".join(_text(item.get("description")) for item in point["events"]))
        lines.extend([
            "",
            "**关键洞察：**",
            point["reason"] or "以对应轮次证据为准。",
            "",
            "若同时存在测试条件变化，应避免把评分变化完全归因于 Prompt 策略。",
            "",
            f"[查看 Round {rnd}](RESPONSES/{_round_title(rnd)})",
            "",
        ])
    return "\n".join(lines)


def _tree_markdown(document: dict[str, Any], nodes: list[dict[str, Any]]) -> str:
    scores = [_score(n) for n in nodes]
    lines = ["# 完整决策树", "", "## 树状结构", "", "```text", "ROOT"]
    for idx, node in enumerate(nodes, 1):
        strategy = _text(node.get("strategy")) or _text(node.get("improvement")) or "unknown"
        score = _score(node)
        prompt = _text(node.get("prompt")).replace("\n", " ")[:80]
        event_mark = " +EVENT" if _events_for_node(document, node) else ""
        lines.append(f"└─ Round {idx} [{score if score is not None else '?'}/10] {strategy}{event_mark} :: {prompt}")
    lines.extend(["```", "", "## 评分趋势可视化", "", f"{scores}", "", "## 关键路径", "", "参见 [ATTACK_PATTERN.md](ATTACK_PATTERN.md) 与 [TURNING_POINTS.md](TURNING_POINTS.md)。", ""])
    return "\n".join(lines)


def _strategy_markdown(nodes: list[dict[str, Any]]) -> str:
    lines = ["# 策略演化路径", "", "## 策略切换决策逻辑", "", "以下时间线从持久化节点生成；具体切换原因以评分理由、人工意见、人工操作和 Working Memory 为准。", "", "## 策略切换时间线", "", "| 时机 | 原策略 | 新策略 | 原因 |", "|------|--------|--------|------|"]
    previous = ""
    for idx, node in enumerate(nodes, 1):
        current = _text(node.get("strategy")) or _text(node.get("improvement")) or "未记录"
        if previous and current != previous:
            lines.append(f"| Round {idx} | {previous} | {current} | {_text(node.get('reason')) or '由后续评分/人工信息驱动'} |")
        previous = current
    lines.extend(["", "## 各策略最佳适用场景", "", "由实际测试结果总结；不要脱离真实轮次自动臆测。", ""])
    return "\n".join(lines)


def _attack_pattern(document: dict[str, Any], nodes: list[dict[str, Any]]) -> str:
    runtime = _runtime(document)
    strategies: dict[str, list[int]] = {}
    for idx, node in enumerate(nodes, 1):
        strategy = _text(node.get("strategy")) or _text(node.get("improvement")) or "未记录"
        strategies.setdefault(strategy, []).append(idx)
    lines = ["# 攻击链路与策略分析", "", "## 攻击阶段划分", "", "阶段划分需结合真实评分趋势、人工操作和转折点复盘。", "", "## 核心攻击链路", "", "参见 [关键转折点](TURNING_POINTS.md) 和完整轮次原文。", "", "## 策略组合有效性分析", "", "| 策略 | 使用轮次 | 效果 | 说明 |", "|------|----------|------|------|"]
    for strategy, rounds in strategies.items():
        scores = [_score(nodes[i - 1]) for i in rounds if _score(nodes[i - 1]) is not None]
        effect = f"最高 {max(scores)}/10" if scores else "未评分"
        lines.append(f"| {strategy} | {','.join(map(str, rounds))} | {effect} | 以轮次原文、评分理由和测试条件为准 |")

    lines.extend(["", "## 测试者特殊操作", ""])
    events = _session_items(runtime, "operator_events")
    if events:
        for item in events:
            lines.append(f"- {_text(item.get('created_at'))} / source={_text(item.get('source_ref')) or 'session-level'} / `{_text(item.get('event_type')) or 'other'}`: {_text(item.get('description'))}")
    else:
        lines.append("无特殊人工操作。")

    lines.extend(["", "## 外部情报（操作员意见）的作用", ""])
    feedback = _session_items(runtime, "feedback")
    if feedback:
        for item in feedback:
            lines.append(f"- {_text(item.get('created_at'))} / source={_text(item.get('source_ref')) or 'session-level'}: {_text(item.get('text'))}")
    else:
        lines.append("无操作员意见。")
    lines.append("")
    return "\n".join(lines)


def sync_report(document: dict[str, Any], report_root: Path) -> Path:
    session_id = _text(document.get("session_id"))
    if not session_id:
        raise ValueError("session_id is required for report archival")
    root = report_root / f"test-report-{session_id}"
    responses = root / "RESPONSES"
    responses.mkdir(parents=True, exist_ok=True)
    nodes = _nodes(document)

    for idx, node in enumerate(nodes, 1):
        (responses / _round_title(idx)).write_text(_round_markdown(document, node, idx, len(nodes)), encoding="utf-8")

    (root / "SUMMARY.md").write_text(_summary(document, nodes), encoding="utf-8")
    (root / "TURNING_POINTS.md").write_text(_turning_markdown(document, nodes), encoding="utf-8")
    (root / "prompt-tree.md").write_text(_tree_markdown(document, nodes), encoding="utf-8")
    (root / "strategy-evolution.md").write_text(_strategy_markdown(nodes), encoding="utf-8")
    (root / "ATTACK_PATTERN.md").write_text(_attack_pattern(document, nodes), encoding="utf-8")
    return root
