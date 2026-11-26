#!/usr/bin/env python3
"""Pin and bundle PyRIT's standard single-slot YAML jailbreak templates.

Run from a checked-out, pinned PyRIT source tree. This is a maintainers' build
script, NOT part of Agent Mode runtime; PyYAML is only needed while vendoring.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.template_guidance import valid_placeholders

UPSTREAM_COMMIT = "695255f6fe299ac7af2876d16fe946f2b7e0aa72"
RELATIVE_SOURCE = Path("pyrit/datasets/jailbreak/templates")
EXCLUDED = {"in_the_wild", "multi_parameter"}
MAX_LENGTH = 20_000
CATEGORIES = {
    "authority_institutional": """
        authority_override classified_briefing alignment_researcher_memo
        pentest_authorization constitutional_override safety_benchmark_eval
        ailab_redteam_simulation system_prompt_injection
    """,
    "philosophical_decision": """
        acausal_defense determinism_argument godel_incompleteness trolley_problem
    """,
    "persona_role": """
        consciousness_upload dual_consciousness emergent_persona fractal_identity_collapse
    """,
    "context_manipulation": """
        context_flood_academic context_hijack cognitive_overload metamorphic_prompt
    """,
    "few_shot": "fewshot_alignment fewshot_escalation fewshot_redteam_eval",
    "fictional_narrative": """
        black_mirror_episode cosmic_horror mirror_universe recursive_simulator
    """,
    "technical_exploit": "glitch_token token_manipulation",
    "emotional_scenario": "medical_emergency",
}
CATEGORIES = {key: set(names.split()) for key, names in CATEGORIES.items()}


def suggested_category(relative: Path) -> str:
    stem = relative.stem
    if relative.parts[0] == "Arth_Singh":
        return next((tag for tag, names in CATEGORIES.items() if stem in names), "unclassified")
    if relative.parts[0] == "pliny":
        return "persona_role"  # Heuristic; not an official PyRIT category.
    if stem.startswith(("dan_", "dude_", "role_play", "aim", "person_gpt",
                        "gpt_4_simulator", "switch", "jedi_mind_trick")):
        return "persona_role"
    if stem.startswith(("dev_mode", "security_researcher")):
        return "authority_institutional"
    if stem.startswith(("cipher_chat", "code_nesting", "table_nesting",
                        "text_continuation", "prefix_injection")):
        return "technical_exploit"
    return "unclassified"


def convert(source: Path, dest: Path, expected_revision: str = UPSTREAM_COMMIT) -> dict:
    source = source.resolve()
    template_root = source / RELATIVE_SOURCE
    if not template_root.is_dir():
        raise FileNotFoundError(f"PyRIT template directory not found: {template_root}")
    if not (source / "LICENSE").is_file():
        raise FileNotFoundError(f"PyRIT LICENSE not found: {source / 'LICENSE'}")
    dest.mkdir(parents=True, exist_ok=True)
    buckets = {"root": [], "arth": [], "pliny": []}
    excluded, skipped = {}, []
    for file in sorted(template_root.rglob("*.yaml")):
        relative = file.relative_to(template_root)
        root_group = relative.parts[0] if len(relative.parts) > 1 else "root"
        if root_group in EXCLUDED:
            excluded[root_group] = excluded.get(root_group, 0) + 1
            continue
        try:
            raw = yaml.safe_load(file.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as err:
            skipped.append({"source_file": relative.as_posix(), "reason": str(err)})
            continue
        if not isinstance(raw, dict):
            skipped.append({"source_file": relative.as_posix(), "reason": "not a YAML mapping"})
            continue
        value = raw.get("value")
        parameters = raw.get("parameters", ["prompt"])
        if (not isinstance(value, str) or not value.strip()
                or len(value) > MAX_LENGTH
                or raw.get("data_type", "text") != "text"
                or not isinstance(parameters, list)
                or any(p not in {"prompt", "objective"} for p in parameters)
                or not valid_placeholders(value)):
            skipped.append({"source_file": relative.as_posix(), "reason": "incompatible or unsafe template"})
            continue
        category = raw.get("category")
        source_type = "source" if isinstance(category, str) and category.strip() else "suggested"
        if not category:
            category = suggested_category(relative)
        record = {
            "id": "pyrit:" + relative.with_suffix("").as_posix(),
            "name": str(raw.get("name") or relative.stem),
            "template": value,
            "category": str(category),
            "classification_source": source_type,
            "description": str(raw.get("description") or ""),
            "authors": raw.get("authors") if isinstance(raw.get("authors"), list) else [],
            "source_url": str(raw.get("source") or ""),
            "source_file": relative.as_posix(),
            "upstream_url": (
                f"https://github.com/microsoft/PyRIT/blob/{expected_revision}/"
                f"{RELATIVE_SOURCE.as_posix()}/{relative.as_posix()}"
            ),
            "source": "PyRIT",
            "upstream_commit": expected_revision,
        }
        bucket = "arth" if root_group == "Arth_Singh" else (
            "pliny" if root_group == "pliny" else "root"
        )
        buckets[bucket].append(record)

    for file in dest.glob("core-*.json"):
        file.unlink()
    output_counts = {}
    for bucket, records in buckets.items():
        if not records:
            continue
        output = dest / f"core-{bucket}.json"
        output.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        output_counts[bucket] = len(records)

    shutil.copyfile(source / "LICENSE", dest / "LICENSE")
    manifest = {
        "upstream": "https://github.com/microsoft/PyRIT",
        "commit": expected_revision,
        "template_root": RELATIVE_SOURCE.as_posix(),
        "bundled": output_counts,
        "total_bundled": sum(output_counts.values()),
        "excluded_by_collection": excluded,
        "skipped": skipped,
        "notes": [
            "Category mappings are suggestions, not verified PyRIT official labels.",
            "in_the_wild contains third-party community prompts; excluded from curated default library.",
            "multi_parameter templates are not compatible with one-slot objective substitution.",
            "Preserve original PyRIT license and source metadata when redistributing.",
        ],
    }
    (dest / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="PyRIT checkout root")
    parser.add_argument("--dest", default=Path(__file__).resolve().parents[1] / "resources" / "pyrit", type=Path)
    args = parser.parse_args()
    print(json.dumps(convert(args.source, args.dest), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
