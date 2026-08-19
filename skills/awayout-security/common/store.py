from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

    def _path(self, session_id: str) -> Path:
        safe = "".join(ch for ch in session_id if ch.isalnum() or ch in {"-", "_"})
        if not safe:
            raise ValueError("invalid session_id")
        return self.directory / f"{safe}.json"

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
        runtime.setdefault("metadata", {})
        runtime.setdefault("working_memory", empty_working_memory())
        runtime.setdefault("created_at", self._now())
        return runtime

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _write_active(self, data: dict[str, Any], runtime: dict[str, Any]) -> None:
        self.active_path.write_text(
            json.dumps(
                {
                    "session_id": data.get("session_id"),
                    "algorithm": data.get("algorithm"),
                    "objective": data.get("objective"),
                    "state": data.get("state"),
                    "updated_at": runtime.get("updated_at"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _archive(self, data: dict[str, Any]) -> Path:
        return sync_report(data, self.report_root)

    def save(self, controller: Controller) -> Path:
        path = self._path(controller.session_id)
        runtime: dict[str, Any] = {}
        if path.is_file():
            try:
                runtime = self._runtime(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                runtime = {
                    "feedback": [],
                    "metadata": {},
                    "working_memory": empty_working_memory(),
                    "created_at": self._now(),
                }
        else:
            runtime = self._runtime({})

        runtime["updated_at"] = self._now()
        data = controller.to_dict()
        data["_runtime"] = runtime
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_active(data, runtime)
        self._archive(data)
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
                sessions.append(
                    {
                        "session_id": data.get("session_id"),
                        "algorithm": data.get("algorithm"),
                        "objective": data.get("objective"),
                        "state": data.get("state"),
                        "updated_at": runtime.get("updated_at"),
                        "feedback_count": len(runtime.get("feedback", [])),
                        "memory_item_count": len(memory.get("items", [])),
                        "report_dir": str(self.report_root / f"test-report-{data.get('session_id')}") if data.get("session_id") else None,
                    }
                )
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
        feedback = runtime.setdefault("feedback", [])
        item = {
            "text": value,
            "created_at": self._now(),
            "state": data.get("state"),
        }
        feedback.append(item)
        runtime["updated_at"] = item["created_at"]
        data["_runtime"] = runtime
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_active(data, runtime)
        self._archive(data)
        return item

    def get_feedback(self, session_id: str) -> list[dict[str, Any]]:
        data = self._read_document(session_id)
        runtime = self._runtime(data)
        return list(runtime.get("feedback", []))

    def add_memory_update(self, session_id: str, update: dict[str, Any]) -> dict[str, Any]:
        path = self._path(session_id)
        data = self._read_document(session_id)
        runtime = self._runtime(data)
        memory = apply_memory_update(runtime, update)
        runtime["updated_at"] = self._now()
        data["_runtime"] = runtime
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_active(data, runtime)
        self._archive(data)
        return memory

    def get_memory_context(self, session_id: str) -> dict[str, Any]:
        return build_memory_context(self._read_document(session_id))

    def set_metadata(self, session_id: str, **values: Any) -> dict[str, Any]:
        path = self._path(session_id)
        data = self._read_document(session_id)
        runtime = self._runtime(data)
        metadata = runtime.setdefault("metadata", {})
        for key, value in values.items():
            if value is not None and str(value).strip():
                metadata[key] = value
        runtime["updated_at"] = self._now()
        data["_runtime"] = runtime
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_active(data, runtime)
        self._archive(data)
        return metadata
