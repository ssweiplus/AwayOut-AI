from __future__ import annotations

import json
from pathlib import Path

from skills.awayout_security.algorithms.pair.controller import PairController


class AgentSessionStore:
    def __init__(self, directory: str = ".awayout-agent"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        safe = "".join(ch for ch in session_id if ch.isalnum() or ch in {"-", "_"})
        if not safe:
            raise ValueError("invalid session_id")
        return self.directory / f"{safe}.json"

    def save(self, controller: PairController) -> Path:
        path = self._path(controller.session_id)
        path.write_text(
            json.dumps(controller.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def load(self, session_id: str) -> PairController:
        path = self._path(session_id)
        if not path.is_file():
            raise FileNotFoundError(f"agent session not found: {session_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        algorithm = str(data.get("algorithm", "PAIR")).upper()
        if algorithm != "PAIR":
            raise ValueError(f"unsupported persisted algorithm: {algorithm}")
        return PairController.from_dict(data)
