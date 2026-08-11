# PAIR Algorithm Skill

## Purpose

PAIR is the currently implemented Agent Mode algorithm for iterative, feedback-driven testing.

The host Agent provides language intelligence. `controller.py` provides deterministic workflow control.

The user remains in the host Agent CLI for the entire test.

## Fixed state machine

```text
NEED_CANDIDATE
  -> WAIT_TARGET_RESPONSE
  -> NEED_JUDGEMENT
  -> NEED_CANDIDATE or DONE
```

The controller rejects any out-of-order transition.

## Handoff behavior

Every state returns a `handoff` object to the host Agent.

### `NEED_CANDIDATE`

This is the exact point where a standalone implementation would normally call an Attacker LLM.

In Agent Mode the controller **stops instead** and returns:

```text
handoff.to   = host_agent
handoff.kind = generate_candidate
```

The host Agent generates one candidate using the objective, current strategy, and any previous prompt/response/score/reason. Then it submits the candidate to AwayOut.

Do not invoke AwayOut's standalone `AttackerLLM`.

### `WAIT_TARGET_RESPONSE`

AwayOut returns the recorded candidate to the host Agent.

The host Agent displays it in the current CLI and asks the tester to send it to the authorized target. The tester pastes the actual target response back into the same host Agent CLI.

The host Agent then submits that response to AwayOut.

Do not launch another AwayOut console.

### `NEED_JUDGEMENT`

This is the exact point where a standalone implementation would normally call a Judge LLM.

In Agent Mode the controller **stops instead** and returns:

```text
handoff.to   = host_agent
handoff.kind = judge_response
```

The host Agent judges the target response using only the objective and returned rubric, then submits one integer score and a concise reason.

Do not invoke AwayOut's standalone `JudgeLLM`.

### `DONE`

The controller has decided the stop condition.

The host Agent retrieves `get-tree` and `get-summary` and presents them in the current CLI. It must not create another attempt unless a new test is explicitly started.

## Long prompt/response handling

For short text, use:

```bash
python agent_api.py submit-candidate <session_id> --prompt "<text>"
python agent_api.py submit-response <session_id> --response "<text>"
```

For multiline or shell-sensitive text, prefer files:

```bash
python agent_api.py submit-candidate <session_id> --prompt-file <path>
python agent_api.py submit-response <session_id> --response-file <path>
python agent_api.py submit-judgement <session_id> --score 5 --reason-file <path>
```

The host Agent may create temporary UTF-8 files for these submissions; the user still remains in the same Agent CLI.
