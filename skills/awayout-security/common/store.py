from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from algorithms.drattack.controller import DrAttackController
from algorithms.pair.controller import PairController
from algorithms.tap.controller import TapController

Controller = PairController | TapController | DrAttackController


class AgentSessionStore:
    def __init__(self, directory: str = ".awayout-agent"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.active_path = self.directory / "active.json"

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

    def _runtime(self, data: dict[str, Any]) -> dict[str, Any]:
        runtime = data.get("_runtime")
        if not isinstance(runtime, dict):
            runtime = {}
        runtime.setdefault("feedback", [])
        return runtime

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def save(self, controller: Controller) -> Path:
        path = self._path(controller.session_id)
        runtime: dict[str, Any] = {}
        if path.is_file():
            try:
                runtime = self._runtime(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                runtime = {"feedback": []}

        runtime["updated_at"] = self._now()
        data = controller.to_dict()
        data["_runtime"] = runtime
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        self.active_path.write_text(
            json.dumps(
                {
                    "session_id": controller.session_id,
                    "algorithm": data.get("algorithm"),
                    "objective": data.get("objective"),
                    "state": data.get("state"),
                    "updated_at": runtime["updated_at"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
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
                sessions.append(
                    {
                        "session_id": data.get("session_id"),
                        "algorithm": data.get("algorithm"),
                        "objective": data.get("objective"),
                        "state": data.get("state"),
                        "updated_at": runtime.get("updated_at"),
                        "feedback_count": len(runtime.get("feedback", [])),
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

        active = {
            "session_id": data.get("session_id"),
            "algorithm": data.get("algorithm"),
            "objective": data.get("objective"),
            "state": data.get("state"),
            "updated_at": runtime["updated_at"],
        }
        self.active_path.write_text(json.dumps(active, ensure_ascii=False, indent=2), encoding="utf-8")
        return item

    def get_feedback(self, session_id: str) -> list[dict[str, Any]]:
        data = self._read_document(session_id)
        runtime = self._runtime(data)
        return list(runtime.get("feedback", []))
