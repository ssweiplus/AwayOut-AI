from __future__ import annotations

import json
from pathlib import Path


def load_seed_prompts(path: str, objective: str, strategy: str) -> list[str]:
    """Load optional seed templates and render {objective} placeholders.

    Expected JSON shape:
    [
      {"name": "...", "strategy": "logical_appeal", "template": "...{objective}..."}
    ]

    `strategy` may be omitted or set to "any".
    Missing files are treated as an empty seed library.
    """
    seed_path = Path(path).expanduser()
    if not seed_path.is_file():
        return []

    with seed_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, list):
        raise ValueError("Seed file must contain a JSON list")

    prompts: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        item_strategy = str(item.get("strategy", "any")).strip() or "any"
        if item_strategy not in {"any", strategy}:
            continue
        template = str(item.get("template", "")).strip()
        if not template:
            continue
        prompts.append(template.replace("{objective}", objective))
    return prompts
