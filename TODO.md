# TODO

## Full test transcript and replay

- [ ] Add an append-only per-session event log alongside the existing session snapshot.
- [ ] Keep the current `S-<id>.json` snapshot for resume/checkpoint recovery.
- [ ] Record ordered test events with timestamps and sequence numbers, including candidate prompts, target-system responses, judgements, state transitions, handoffs, and operator feedback.
- [ ] Add a replay/transcript command, e.g. `python api.py replay <session_id>`, to reconstruct the full test timeline for review and auditing.
- [ ] Keep replay data separate from controller state so event history cannot affect deterministic resume behavior.

Suggested storage model:

```text
.awayout-agent/
├── active.json
├── S-001.json
└── S-001.events.jsonl
```

Design intent:

```text
Session snapshot -> where are we now? -> resume/checkpoint
Event log        -> how did we get here? -> transcript/replay/audit
```

## Cross-algorithm protocol parity

- [x] Add structured `objective_guard` / `mutation_goal` protection to DrAttack so PAIR, TAP and DrAttack all externalize the original-objective contract.
- [ ] When adding or changing shared Agent Mode behavior, verify PAIR, TAP and DrAttack all receive equivalent support where applicable: checkpoint/resume, operator marker reminders, persisted human feedback, objective preservation, handoff semantics and completion rules.
- [ ] Keep common interaction/recovery behavior in shared API/store layers when possible instead of duplicating it in individual algorithms.
- [ ] Update each algorithm `SKILL.md` when an algorithm-specific handoff or interaction requirement differs from the shared top-level protocol.

## DrAttack execution semantics

- [ ] Redesign DrAttack if true `stop_on_success` is required. The current controller collects and scores all configured strategies as one batch, so the compatibility flag cannot provide real first-success early stopping.
- [ ] If sequential early-stop is implemented, define deterministic per-strategy ordering, response collection, scoring transitions, resume behavior and operator interaction before advertising `stop_on_success` as a normal configuration option.

## Skill packaging discipline

- [x] Keep top-level `skills/awayout-security/SKILL.md` focused on startup routing and global invariants.
- [x] Keep algorithm configuration/state-machine details in each `algorithms/<name>/SKILL.md`.
- [x] Keep install/dependency/troubleshooting guidance in `skills/awayout-security/INSTALL.md`.
- [ ] For future features, preserve the Agent Mode dependency boundary: `skills/awayout-security/` must remain self-contained and must not silently depend on root-level Standalone/compatibility files.
