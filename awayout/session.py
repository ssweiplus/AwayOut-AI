from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class IterationRecord:
    iteration: int
    strategy: str
    improvement: str
    generated_prompt: str
    sent_prompt: str
    human_modified: bool
    target_response: str
    judge_score: int
    judge_reason: str
    tester_note: str = ""
    conversation_mode: str = "continue"


@dataclass
class TestSession:
    objective: str
    attacker_model: str
    judge_model: str
    threshold: int
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    records: list[IterationRecord] = field(default_factory=list)

    def add(self, record: IterationRecord) -> None:
        self.records.append(record)

    @property
    def best(self) -> IterationRecord | None:
        if not self.records:
            return None
        return max(self.records, key=lambda item: item.judge_score)

    def to_dict(self) -> dict:
        return {
            "objective": self.objective,
            "attacker_model": self.attacker_model,
            "judge_model": self.judge_model,
            "threshold": self.threshold,
            "created_at": self.created_at,
            "records": [asdict(record) for record in self.records],
        }

    def save(self, directory: str = "sessions") -> Path:
        output_dir = Path(directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = output_dir / f"session-{stamp}.json"
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path
