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
├── api.py
├── doctor.py
├── common/
│   └── store.py
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

Do not copy only `SKILL.md`; the controllers, API and store are part of the skill runtime.

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

The doctor checks:

```text
- Python version
- required Agent Mode files
- PAIR/TAP/DrAttack imports
- controller startup
- core deterministic behavior checks
- session read/write persistence
```

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

AwayOut creates session data under:

```text
.awayout-agent/
```

This directory is runtime state, not an installation dependency. Keep it if you want to resume existing tests; it may be removed if you intentionally want to discard local session state.

## Troubleshooting

### Python is missing or older than 3.10

Install/select Python 3.10+ and rerun:

```bash
python doctor.py
```

### Required skill file missing

Restore the complete `awayout-security` directory. Do not replace individual controller/API files with unrelated revisions.

### Controller import failure

Confirm `api.py`, `common/` and all three `algorithms/*` directories come from the same revision.

### Session store is not writable

Run from a writable directory or specify another store location:

```bash
python api.py --store <writable-path> get-active
```

### Session ID forgotten

```bash
python api.py get-active
python api.py list-sessions
```

### Agent stopped unexpectedly

```bash
python api.py resume
```

Persisted state is authoritative. Repeat only work that had not yet been successfully submitted/checkpointed.

### Invalid transition

Inspect current state:

```bash
python api.py get-state <session_id>
```

Then perform only the returned action. For payload details, read the selected algorithm's `SKILL.md`.

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