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
