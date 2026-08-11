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

- [ ] Add the same structured `objective_guard` / `mutation_goal` protection to DrAttack that PAIR and TAP already expose.
- [ ] When adding or changing shared Agent Mode behavior, verify PAIR, TAP and DrAttack all receive equivalent support where applicable: checkpoint/resume, operator marker reminders, persisted human feedback, objective preservation, handoff semantics and completion rules.
- [ ] Keep common interaction/recovery behavior in shared API/store layers when possible instead of duplicating it in individual algorithms.
- [ ] Update each algorithm `SKILL.md` when an algorithm-specific handoff or interaction requirement differs from the shared top-level protocol.
