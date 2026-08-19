# AwayOut Agent Mode Installation

This guide applies only to `skills/awayout-security/` Agent Mode.

## Requirements

```text
Python 3.10+
Third-party Python packages: none
External LLM/model provider: none required by AwayOut Agent Mode
```

The host Agent/CLI supplies language reasoning. AwayOut itself uses only the Python standard library in Agent Mode.

## Install

Copy the complete `awayout-security` directory into the location from which your host Agent can read/use the skill.

Required layout:

```text
awayout-security/
├── SKILL.md
├── INSTALL.md
├── REPORTING.md
├── api.py
├── doctor.py
├── common/
│   ├── store.py
│   ├── presenter.py
│   ├── scoring.py
│   ├── memory.py
│   └── report.py
└── algorithms/
    ├── pair/
    │   ├── SKILL.md
    │   └── controller.py
    ├── tap/
    │   ├── SKILL.md
    │   └── controller.py
    └── drattack/
        ├── SKILL.md
        └── controller.py
```

Do not copy only `SKILL.md`; controllers, API, presenter, scoring, Working Memory, report archiver and store are part of the runtime.

Do not mix files from different revisions.

## Verify

From the `awayout-security` directory:

```bash
python doctor.py
```

Expected final line:

```text
Agent Mode is ready. No external LLM provider is required.
```

The doctor checks Python/version, required files, controller startup, user-facing interaction contracts, internal-only boundaries, scoring anchors, Working Memory compatibility/persistence, report creation and session restore.

## First run / recovery

Before starting a new test:

```bash
python api.py get-active
```

If an unfinished session exists:

```bash
python api.py resume
```

Otherwise follow `SKILL.md` to collect the objective and choose an algorithm.

## Runtime data

Execution state:

```text
.awayout-agent/
```

Permanent test archive (sibling of the store directory when using the default store):

```text
test-report-S-xxxxxxxxxx/
```

The report directory is refreshed on session saves and runtime metadata/memory updates. Keep it for review/audit even if the session later ends or is discarded.

Working Memory is stored inside each session document under:

```text
_runtime.working_memory
```

It is auxiliary context only. Full raw Prompt/Response history remains in the controller/session and `test-report-*/RESPONSES/`.

## Working Memory commands

Inspect mutation context:

```bash
python -m common.memory context <session_id>
```

Persist a scoring-time memory extraction:

```bash
python -m common.memory update <session_id> --data-file memory-update.json
```

Record target-system metadata when known:

```bash
python -m common.memory metadata <session_id> --target-system "<target>"
```

## Troubleshooting

### Python is missing or older than 3.10

Install/select Python 3.10+ and rerun `python doctor.py`.

### Required skill file missing

Restore the complete `awayout-security` directory. Do not replace individual files with unrelated revisions.

### Controller import failure

Confirm `api.py`, `common/` and all three `algorithms/*` directories come from the same revision.

### Session store is not writable

Run from a writable directory or specify another store location:

```bash
python api.py --store <writable-path> get-active
```

The report root becomes the parent directory of that store.

### Agent stopped unexpectedly

```bash
python api.py resume
```

Persisted state is authoritative. Repeat only work that had not yet been successfully submitted/checkpointed.

### Invalid transition

```bash
python api.py get-state <session_id>
```

Perform only the returned action.

### Report looks incomplete

Check the matching session JSON first. The archiver never invents missing raw content. If a Prompt/response/score was never persisted, the report cannot reconstruct it from chat history.

### Shell quoting / multiline content

Prefer file-based arguments such as:

```text
--data-file
--prompt-file
--response-file
--reason-file
--feedback-file
```

## Dependency rule for future changes

Agent Mode must remain self-contained under `skills/awayout-security/`. If a future feature adds a dependency, update this file and `doctor.py` in the same change.
