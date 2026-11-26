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
├── TEMPLATES.md
├── api.py
├── doctor.py
├── common/
│   ├── store.py
│   ├── template_guidance.py
│   ├── presenter.py
│   ├── interaction.py
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
└── resources/
    └── pyrit/
        ├── core-root.json
        ├── core-arth.json
        ├── core-pliny.json
        ├── manifest.json
        └── LICENSE
```

Do not copy only `SKILL.md`; controllers, API, presenter, interaction parser, scoring, Working Memory, report archiver and store are part of the runtime.

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

The doctor checks Python/version, required files, the bundled 151 PyRIT prompt references and safe placeholders, controller startup, user-facing interaction contracts, internal-only boundaries, scoring anchors, Working Memory compatibility/persistence, report creation and session restore.

## First run / recovery

Before starting a new test:

```bash
python api.py get-active
```

If an unfinished session exists:

```bash
python api.py resume
```

To recover an older session instead of the most recently active one:

```bash
python api.py list-sessions
python api.py resume --session-id S-xxxxxxxxxx
```

To increase the budget on a completed session without replacing its history:

```bash
python api.py extend-test S-xxxxxxxxxx --extra-iterations 5  # PAIR
python api.py extend-test S-xxxxxxxxxx --extra-depth 2       # TAP
python api.py extend-test S-xxxxxxxxxx --extra-reconstructions 1 # DrAttack
```

The extension is explicitly recorded as a `budget_extended` operator event.
PAIR preserves scored nodes; TAP continues from scored surviving branches;
DrAttack appends a new reconstruction batch using the existing semantic fragments.
When a first-success stop policy ended a run, `--continue-after-success` is
required to override that stopping condition.

Otherwise follow `SKILL.md` to collect the objective and choose an algorithm.

## Human target-response input

Preferred entrypoint:

```bash
python api.py submit-user-input <session_id> --message-file user-input.txt --request-id response-001
```

Normal case: `user-input.txt` contains only the complete target-system response, with no marker.

When special tester actions or operator comments must be recorded together with the response, use the optional blocks documented by the presenter and `SKILL.md`:

```text
[[AWAYOUT:EVENT]]
...

[[AWAYOUT:OPERATOR]]
...

[[AWAYOUT:RESPONSE]]
...
```

Do not manually split these blocks in the host Agent; `common/interaction.py` owns parsing.

## Runtime data

Execution state:

```text
.awayout-agent/
```

Permanent test archive (sibling of the store directory when using the default store):

```text
test-report-S-xxxxxxxxxx/
```

The report directory is refreshed on session saves and runtime metadata/memory/operator updates. Keep it for review/audit even if the session later ends or is discarded.

Runtime auxiliary data is stored under `_runtime`, including:

```text
working_memory
feedback
operator_events
metadata
template_config
template_uses
submitted_requests
```

These do not replace full raw Prompt/Response history.

## Working Memory commands

Inspect mutation context:

```bash
python -m common.memory context <session_id>
```

Persist a scoring-time memory extraction:

```bash
python -m common.memory update <session_id> --data-file memory-update.json --request-id memory-001
```

Record target-system metadata when known:

```bash
python -m common.memory metadata <session_id> --target-system "<target>" --request-id metadata-001
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

Persisted state is authoritative. Repeat only work that had not yet been successfully
submitted/checkpointed. Every mutating `api.py` command supports an optional
`--request-id`. Always reuse the **same request-id and payload** for an uncertain
submission. If already committed, the API returns the current checkpoint with
`result.idempotency.replayed=true` and does not repeat the action. The same ID
with a different payload is rejected. Identical payloads submitted with **different**
IDs are NOT deduplicated. Requests without a request ID remain backwards compatible.

Session records are atomically replaced and API mutations on one session hold a
cross-process OS file lock. Markdown reports are regenerated after state saves.
A crash before the state write leaves the old checkpoint; a crash after the state
write can be retried safely with the same ID. Note that this protects the AwayOut
record, not external target-system actions. `start-test` itself has no request-ID
deduplication because each invocation creates a new session.

### Invalid transition

```bash
python api.py get-state <session_id>
```

Perform only the returned action.

### Tester input is rejected

If no AwayOut marker is needed, paste the target response directly. If any `[[AWAYOUT:*]]` marker is used and the same message also contains a target response, put that response under `[[AWAYOUT:RESPONSE]]`. Do not leave unlabelled text before the first advanced-mode block.

### Report looks incomplete

Check the matching session JSON first. The archiver never invents missing raw content. If a Prompt/response/score was never persisted, the report cannot reconstruct it from chat history.

### Shell quoting / multiline content

Prefer file-based arguments such as:

```text
--message-file
--data-file
--prompt-file
--response-file
--reason-file
--feedback-file
```

## Dependency rule for future changes

Agent Mode must remain self-contained under `skills/awayout-security/`. If a future feature adds a dependency, update this file and `doctor.py` in the same change.
