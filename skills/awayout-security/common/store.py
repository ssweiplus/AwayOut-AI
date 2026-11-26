from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from algorithms.drattack.controller import DrAttackController
from algorithms.pair.controller import PairController
from algorithms.tap.controller import TapController
from common.memory import apply_memory_update, build_memory_context, empty_working_memory
from common.report import sync_report

Controller = PairController | TapController | DrAttackController


class AgentSessionStore:
    def __init__(self, directory: str = ".awayout-agent"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.active_path = self.directory / "active.json"
        self.report_root = self.directory.parent
        self._pending_request: dict[str, Any] | None = None

    def _path(self, session_id: str) -> Path:
        safe = "".join(ch for ch in session_id if ch.isalnum() or ch in {"-", "_"})
        if not safe:
            raise ValueError("invalid session_id")
        return self.directory / f"{safe}.json"

    @contextmanager
    def session_lock(self, session_id: str):
        """Cross-process lock released by the OS after a process crash.

        Use the same lock around the replay check and the state mutation.
        """
        path = self._path(session_id).with_suffix(".lock")
        with path.open("a+b") as handle:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def get_request(self, session_id: str, request_id: str) -> dict[str, Any] | None:
        runtime = self._read_document(session_id).get("_runtime", {})
        return next((entry for entry in runtime.get("submitted_requests", [])
                     if isinstance(entry, dict) and entry.get("request_id") == request_id), None)

    def set_pending_request(self, receipt: dict[str, Any] | None) -> None:
        self._pending_request = receipt

    def _attach_request(self, runtime: dict[str, Any]) -> None:
        if self._pending_request is not None:
            runtime.setdefault("submitted_requests", []).append({
                **self._pending_request, "recorded_at": self._now()
            })

    def _atomic_json(self, path: Path, data: dict[str, Any]) -> None:
        temp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)

    def _read_document(self, session_id: str) -> dict[str, Any]:
        path = self._path(session_id)
        if not path.is_file():
            raise FileNotFoundError(f"agent session not found: {session_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"invalid session document: {session_id}")
        return data

    def get_document(self, session_id: str) -> dict[str, Any]:
        return self._read_document(session_id)

    def _runtime(self, data: dict[str, Any]) -> dict[str, Any]:
        runtime = data.get("_runtime")
        if not isinstance(runtime, dict):
            runtime = {}
        runtime.setdefault("feedback", [])
        runtime.setdefault("operator_events", [])
        runtime.setdefault("metadata", {})
        runtime.setdefault("working_memory", empty_working_memory())
        runtime.setdefault("created_at", self._now())
        return runtime

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _current_source_ref(self, data: dict[str, Any]) -> str | None:
        algorithm = str(data.get("algorithm", "")).upper()
        state = str(data.get("state", ""))
        if algorithm == "PAIR":
            node_id = data.get("current_node_id")
            return str(node_id) if node_id else None
        if algorithm == "TAP" and state == "WAIT_TARGET_RESPONSES":
            current_ids = list(data.get("current_ids", []))
            index = int(data.get("current_response_index", 0))
            if 0 <= index < len(current_ids):
                return str(current_ids[index])
        if algorithm in {"DRATTACK", "DR_ATTACK"} and state == "WAIT_BASELINE_RESPONSE":
            return "baseline"
        if algorithm in {"DRATTACK", "DR_ATTACK"} and state == "WAIT_STRATEGY_RESPONSES":
            nodes = [n for n in data.get("strategy_nodes", []) if isinstance(n, dict)]
            index = int(data.get("current_strategy_index", 0))
            if 0 <= index < len(nodes):
                return str(nodes[index].get("strategy") or "") or None
        return None

    def _write_active(self, data: dict[str, Any], runtime: dict[str, Any]) -> None:
        self._atomic_json(self.active_path, {
            "session_id": data.get("session_id"),
            "algorithm": data.get("algorithm"),
            "objective": data.get("objective"),
            "state": data.get("state"),
            "updated_at": runtime.get("updated_at"),
        })

    def _persist_runtime(self, path: Path, data: dict[str, Any], runtime: dict[str, Any]) -> None:
        runtime["updated_at"] = self._now()
        self._attach_request(runtime)
        data["_runtime"] = runtime
        self._atomic_json(path, data)
        self._write_active(data, runtime)
        self._archive(data)

    def _archive(self, data: dict[str, Any]) -> Path:
        return sync_report(data, self.report_root)

    def save(self, controller: Controller, *,
             template_uses: list[tuple[str, dict[str, Any]]] | None = None,
             memory_update: dict[str, Any] | None = None,
             template_config: dict[str, Any] | None = None,
             feedback_texts: list[str] | None = None,
             operator_events: list[dict[str, Any]] | None = None) -> Path:
        path = self._path(controller.session_id)
        previous = self._read_document(controller.session_id) if path.is_file() else {}
        runtime = self._runtime(previous)
        previous_state = previous.get("state")
        previous_ref = self._current_source_ref(previous)
        for comment in feedback_texts or []:
            value = str(comment).strip()
            if not value:
                raise ValueError("feedback cannot be empty")
            runtime.setdefault("feedback", []).append({
                "text": value, "created_at": self._now(),
                "state": previous_state, "source_ref": previous_ref,
            })
        for event in operator_events or []:
            value = str(event.get("description", "")).strip()
            if not value:
                raise ValueError("operator event description cannot be empty")
            runtime.setdefault("operator_events", []).append({
                "event_type": str(event.get("event_type", "other")).strip() or "other",
                "description": value,
                "timing": str(event.get("timing", "unspecified")).strip() or "unspecified",
                "details": event.get("details") if isinstance(event.get("details"), dict) else {},
                "created_at": self._now(),
                "state": previous_state, "source_ref": previous_ref,
            })
        if memory_update is not None:
            apply_memory_update(runtime, memory_update)
        if template_config is not None:
            runtime["template_config"] = dict(template_config)
        if template_uses:
            recorded = runtime.setdefault("template_uses", [])
            for source_ref, use in template_uses:
                if not source_ref:
                    raise ValueError("template use requires a source reference")
                recorded[:] = [item for item in recorded
                               if item.get("source_ref") != source_ref]
                recorded.append({
                    "source_ref": source_ref, **use, "recorded_at": self._now(),
                })
        data = controller.to_dict()
        self._persist_runtime(path, data, runtime)
        return path

    def load(self, session_id: str) -> Controller:
        data = self._read_document(session_id)
        algorithm = str(data.get("algorithm", "PAIR")).upper()
        if algorithm == "PAIR":
            return PairController.from_dict(data)
        if algorithm == "TAP":
            return TapController.from_dict(data)
        if algorithm in {"DRATTACK", "DR_ATTACK"}:
            return DrAttackController.from_dict(data)
        raise ValueError(f"unsupported persisted algorithm: {algorithm}")

    def get_active(self) -> dict[str, Any] | None:
        if not self.active_path.is_file():
            return None
        data = json.loads(self.active_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not data.get("session_id"):
            return None
        return data

    def activate(self, session_id: str) -> Controller:
        data = self._read_document(session_id)
        self._write_active(data, self._runtime(data))
        return self.load(session_id)

    def load_active(self) -> Controller:
        active = self.get_active()
        if not active:
            raise FileNotFoundError("no active AwayOut session")
        return self.load(str(active["session_id"]))

    def list_sessions(self) -> list[dict[str, Any]]:
        sessions: list[dict[str, Any]] = []
        for path in self.directory.glob("S-*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue
                runtime = self._runtime(data)
                memory = runtime.get("working_memory") if isinstance(runtime.get("working_memory"), dict) else {}
                sessions.append({
                    "session_id": data.get("session_id"),
                    "algorithm": data.get("algorithm"),
                    "objective": data.get("objective"),
                    "state": data.get("state"),
                    "updated_at": runtime.get("updated_at"),
                    "feedback_count": len(runtime.get("feedback", [])),
                    "operator_event_count": len(runtime.get("operator_events", [])),
                    "memory_item_count": len(memory.get("items", [])),
                    "report_dir": str(self.report_root / f"test-report-{data.get('session_id')}") if data.get("session_id") else None,
                })
            except Exception:
                continue
        sessions.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        return sessions

    def add_feedback(self, session_id: str, text: str) -> dict[str, Any]:
        value = text.strip()
        if not value:
            raise ValueError("feedback cannot be empty")
        path = self._path(session_id)
        data = self._read_document(session_id)
        runtime = self._runtime(data)
        item = {
            "text": value,
            "created_at": self._now(),
            "state": data.get("state"),
            "source_ref": self._current_source_ref(data),
        }
        runtime.setdefault("feedback", []).append(item)
        self._persist_runtime(path, data, runtime)
        return item

    def get_feedback(self, session_id: str) -> list[dict[str, Any]]:
        data = self._read_document(session_id)
        return list(self._runtime(data).get("feedback", []))

    def add_operator_event(
        self,
        session_id: str,
        event_type: str,
        description: str,
        timing: str = "unspecified",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        value = description.strip()
        if not value:
            raise ValueError("operator event description cannot be empty")
        path = self._path(session_id)
        data = self._read_document(session_id)
        runtime = self._runtime(data)
        item = {
            "event_type": (event_type or "other").strip() or "other",
            "description": value,
            "timing": (timing or "unspecified").strip() or "unspecified",
            "details": details if isinstance(details, dict) else {},
            "created_at": self._now(),
            "state": data.get("state"),
            "source_ref": self._current_source_ref(data),
        }
        runtime.setdefault("operator_events", []).append(item)
        self._persist_runtime(path, data, runtime)
        return item

    def get_operator_events(self, session_id: str) -> list[dict[str, Any]]:
        data = self._read_document(session_id)
        return list(self._runtime(data).get("operator_events", []))

    def add_memory_update(self, session_id: str, update: dict[str, Any]) -> dict[str, Any]:
        path = self._path(session_id)
        data = self._read_document(session_id)
        runtime = self._runtime(data)
        memory = apply_memory_update(runtime, update)
        self._persist_runtime(path, data, runtime)
        return memory

    def get_memory_context(self, session_id: str) -> dict[str, Any]:
        return build_memory_context(self._read_document(session_id))

    def set_template_config(self, session_id: str, mode: str, limit: int) -> dict[str, Any]:
        path = self._path(session_id)
        data = self._read_document(session_id)
        runtime = self._runtime(data)
        runtime["template_config"] = {"mode": mode, "limit": limit}
        self._persist_runtime(path, data, runtime)
        return runtime["template_config"]

    def record_template_use(self, session_id: str, source_ref: str, use: dict[str, Any]) -> dict[str, Any]:
        """Persist actual template decisions by stable node/strategy reference."""
        if not source_ref:
            raise ValueError("template use requires a source reference")
        path = self._path(session_id)
        data = self._read_document(session_id)
        runtime = self._runtime(data)
        records = runtime.setdefault("template_uses", [])
        record = {"source_ref": source_ref, **use, "recorded_at": self._now()}
        records[:] = [x for x in records if x.get("source_ref") != source_ref]
        records.append(record)
        self._persist_runtime(path, data, runtime)
        return record

    def set_metadata(self, session_id: str, **values: Any) -> dict[str, Any]:
        path = self._path(session_id)
        data = self._read_document(session_id)
        runtime = self._runtime(data)
        metadata = runtime.setdefault("metadata", {})
        for key, value in values.items():
            if value is not None and str(value).strip():
                metadata[key] = value
        self._persist_runtime(path, data, runtime)
        return metadata
