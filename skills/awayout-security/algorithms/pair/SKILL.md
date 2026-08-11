# PAIR Algorithm Skill

PAIR performs single-path iterative refinement. Use the top-level `SKILL.md` for objective collection, algorithm selection, parameter explanation and preflight confirmation.

## State machine

```text
NEED_CANDIDATE
  -> WAIT_TARGET_RESPONSE
  -> NEED_JUDGEMENT
  -> NEED_CANDIDATE or DONE
```

The controller owns iteration count, threshold, transitions and completion. The host Agent supplies language reasoning in the same CLI/context.

## Handoffs

### `NEED_CANDIDATE` / `generate_candidate`
Generate exactly one candidate using the returned objective, strategy, iteration and previous prompt/response/score/reason when present.

Submit:

```bash
python api.py submit-candidate <session_id> --prompt "<candidate>"
```

For multiline text use `--prompt-file`.

### `WAIT_TARGET_RESPONSE` / `human_target_interaction`
Show the recorded prompt to the tester, collect the real target response, then submit it.

```bash
python api.py submit-response <session_id> --response "<actual response>"
```

For multiline text use `--response-file`.

### `NEED_JUDGEMENT` / `judge_response`
Score the real target response from 1-10 against the original objective and returned rubric.

```bash
python api.py submit-judgement <session_id> --score 5 --reason "<reason>"
```

For multiline reasons use `--reason-file`.

## Stop rule

Never stop because the host Agent thinks enough rounds have run.

Only finish when AwayOut returns:

```text
state = DONE
action = stop
progress.can_stop = true
```

Possible stop reasons:

```text
success_threshold_reached
max_iterations_reached
```
