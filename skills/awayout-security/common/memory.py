from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.report import sync_report

MEMORY_TYPES = {
    "exact_fact",
    "confirmed_fact",
    "useful_clue",
    "blocker",
    "partial_achievement",
    "next_step_hint",
}
RELATIONS = {"direct", "supporting", "incidental"}
STATUSES = {"candidate", "confirmed", "reinforced", "stale", "superseded"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_working_memory() -> dict[str, Any]:
    return {"version": 1, "items": [], "updated_at": None}


def memory_extraction_contract() -> dict[str, Any]:
    return {
        "purpose": "Preserve high-value details for later mutation without replacing raw responses.",
        "rules": [
            "Raw Prompt and target response remain authoritative and must never be replaced by memory summaries.",
            "Extract only information supported by the actual target response or explicit operator feedback.",
            "Preserve exact identifiers verbatim: table/field names, paths, URLs, parameter names, IDs, error codes, tool names, exact returned values, and other precision-sensitive strings.",
            "Separate confidence from relevance/importance; a highly certain but irrelevant fact must not drive mutation.",
            "Mark relation_to_objective as direct/supporting/incidental. Incidental items may be retained but must not redefine the objective.",
            "Use evidence snippets so older details can be recovered without replaying every historical response.",
            "If new evidence contradicts an older item, mark the older item stale or superseded instead of silently deleting history.",
        ],
        "item_schema": {
            "type": sorted(MEMORY_TYPES),
            "content": "concise semantic statement; exact_fact values must preserve spelling exactly",
            "details": "optional structured details",
            "evidence": "short verbatim or faithful evidence snippet from the target response",
            "source_ref": "round/node/strategy identifier",
            "confidence": "0.0..1.0",
            "importance": "1..10",
            "relevance_to_objective": "1..10",
            "relation_to_objective": sorted(RELATIONS),
            "status": sorted(STATUSES),
        },
    }


def _clamp_float(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def normalize_memory_update(update: dict[str, Any], created_at: str | None = None) -> dict[str, Any]:
    stamp = created_at or _now()
    raw_items = update.get("items", []) if isinstance(update, dict) else []
    items: list[dict[str, Any]] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        item_type = str(raw.get("type", "useful_clue")).strip()
        if item_type not in MEMORY_TYPES:
            item_type = "useful_clue"
        content = str(raw.get("content", "")).strip()
        if not content:
            continue
        relation = str(raw.get("relation_to_objective", "supporting")).strip()
        if relation not in RELATIONS:
            relation = "supporting"
        status = str(raw.get("status", "candidate")).strip()
        if status not in STATUSES:
            status = "candidate"
        details = raw.get("details", {})
        if not isinstance(details, (dict, list, str, int, float, bool)) and details is not None:
            details = str(details)
        items.append({
            "type": item_type,
            "content": content,
            "details": details,
            "evidence": str(raw.get("evidence", "")).strip(),
            "source_ref": str(raw.get("source_ref", "")).strip(),
            "confidence": _clamp_float(raw.get("confidence"), 0.0, 1.0, 0.7),
            "importance": _clamp_int(raw.get("importance"), 1, 10, 5),
            "relevance_to_objective": _clamp_int(raw.get("relevance_to_objective"), 1, 10, 5),
            "relation_to_objective": relation,
            "status": status,
            "created_at": stamp,
        })
    return {"items": items}


def apply_memory_update(runtime: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    memory = runtime.get("working_memory")
    if not isinstance(memory, dict):
        memory = empty_working_memory()
    memory.setdefault("version", 1)
    existing = memory.setdefault("items", [])
    existing.extend(normalize_memory_update(update)["items"])
    memory["updated_at"] = _now()
    runtime["working_memory"] = memory
    return memory


def build_memory_context(document: dict[str, Any], max_semantic: int = 12, max_evidence: int = 6) -> dict[str, Any]:
    runtime = document.get("_runtime") if isinstance(document.get("_runtime"), dict) else {}
    memory = runtime.get("working_memory") if isinstance(runtime.get("working_memory"), dict) else empty_working_memory()
    items = [item for item in memory.get("items", []) if isinstance(item, dict)]
    active = [item for item in items if item.get("status") not in {"stale", "superseded"}]
    exact = [item for item in active if item.get("type") == "exact_fact"]
    semantic = [item for item in active if item.get("type") != "exact_fact"]
    semantic.sort(key=lambda item: (int(item.get("relevance_to_objective", 0)), int(item.get("importance", 0)), float(item.get("confidence", 0))), reverse=True)
    evidence = [item for item in active if str(item.get("evidence", "")).strip()]
    evidence.sort(key=lambda item: (int(item.get("relevance_to_objective", 0)), int(item.get("importance", 0))), reverse=True)
    return {
        "policy": "objective + exact facts + top semantic memory + recent full response + top evidence",
        "exact_facts": exact,
        "semantic_memory": semantic[:max_semantic],
        "evidence_snippets": [{"source_ref": item.get("source_ref"), "type": item.get("type"), "evidence": item.get("evidence")} for item in evidence[:max_evidence]],
        "raw_history_rule": "Always keep full raw history in the session/report. For mutation, include the most recent full target response by default; retrieve older raw text only when memory/evidence indicates it is needed.",
    }


def _session_path(store: Path, session_id: str) -> Path:
    safe = "".join(ch for ch in session_id if ch.isalnum() or ch in {"-", "_"})
    if not safe:
        raise ValueError("invalid session_id")
    return store / f"{safe}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="AwayOut working-memory helper")
    parser.add_argument("--store", default=".awayout-agent")
    sub = parser.add_subparsers(dest="command", required=True)

    update = sub.add_parser("update")
    update.add_argument("session_id")
    update.add_argument("--data")
    update.add_argument("--data-file")
    update.add_argument("--request-id", default=None)

    show = sub.add_parser("context")
    show.add_argument("session_id")

    metadata = sub.add_parser("metadata")
    metadata.add_argument("session_id")
    metadata.add_argument("--target-system")
    metadata.add_argument("--request-id", default=None)

    args = parser.parse_args()
    # Local import avoids a module import cycle (store imports memory helpers).
    # Route writes through AgentSessionStore so API and memory CLI share the
    # same cross-process lock and atomic session checkpoint format.
    from common.store import AgentSessionStore

    store = AgentSessionStore(args.store)
    if args.command == "context":
        result = {"success": True, "memory_context": store.get_memory_context(args.session_id)}
    else:
        with store.session_lock(args.session_id):
            if args.command == "update":
                if args.data and args.data_file:
                    raise ValueError("use either --data or --data-file")
                raw = (Path(args.data_file).read_text(encoding="utf-8")
                       if args.data_file else (args.data or ""))
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError("memory update must be an object")
                value = data.get("memory_update", data)
                if not isinstance(value, dict):
                    raise ValueError("memory update must be an object")
            elif args.command == "metadata":
                value = {"target_system": args.target_system}
            else:
                raise ValueError(f"unexpected command: {args.command}")

            if args.request_id is not None:
                if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}", args.request_id):
                    raise ValueError("invalid request-id")
                canonical = json.dumps(
                    {"command": "memory:" + args.command, "payload": value},
                    ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                previous = store.get_request(args.session_id, args.request_id)
                if previous:
                    if previous.get("digest") != digest:
                        raise ValueError("request-id already used with different content")
                    current = store.get_document(args.session_id).get("_runtime", {})
                    result = {"success": True, "idempotency": {"replayed": True,
                                          "request_id": args.request_id},
                              "working_memory": current.get("working_memory")}
                    if args.command == "metadata":
                        result.pop("working_memory", None)
                        result["metadata"] = current.get("metadata", {})
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    return 0
                store.set_pending_request({"request_id": args.request_id,
                                           "digest": digest, "command": "memory:" + args.command})
            if args.command == "update":
                result_value = store.add_memory_update(args.session_id, value)
                result = {"success": True, "working_memory": result_value}
            else:
                meta = store.set_metadata(args.session_id, target_system=args.target_system)
                result = {"success": True, "metadata": meta}

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
