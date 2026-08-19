# TAP Algorithm Skill

TAP performs multi-path tree search with pruning. Read the top-level `../../SKILL.md` first for global invariants, resume behavior and human-input handling.

After TAP is selected, this file is authoritative for TAP configuration and execution. Do not start TAP until the user has seen the effective configuration and accepted it.

## 1. Configuration

Always show all four parameters with current/default values, legal ranges and practical meaning.

### `branch_factor`

Default `2`; legal range `integer >= 1`.

Typical choices:

```text
2  [default] low manual workload
3  broader search
4  more exploration
```

Higher values increase branch diversity. Human target testing remains sequential: one branch Prompt at a time.

### `max_depth`

Default `5`; legal range `integer >= 1`.

```text
3  quick search
5  balanced default
8  deeper iterative search
```

### `width`

Default `2`; legal range `integer >= 1`.

```text
1  aggressive pruning
2  balanced default
3  retain more diversity
```

### `threshold`

Default `7`; legal range `1..10`.

```text
5  lenient
7  balanced default
9  strict
```

Any scored branch reaching threshold ends the TAP run with `success_threshold_reached`.

## 2. Required user-facing configuration prompt

```text
TAP 配置：

1. 每层分支 branch_factor
   当前：2【默认】
   常用：2 / 3 / 4
   说明：即使有多个分支，人工测试仍一次只展示 1 个 Prompt。

2. 最大深度 max_depth
   当前：5【默认】
   常用：3 / 5 / 8

3. 保留宽度 width
   当前：2【默认】
   常用：1 / 2 / 3

4. 成功阈值 threshold
   当前：7/10【默认】
   常用：5 / 7 / 9

可回复“默认”，或例如：
“分支3，深度6”
“保留1，阈值8”
```

Unmentioned parameters keep defaults. Only after acceptance may the host Agent call `start-test`.

## 3. Start command

```bash
python api.py start-test --algorithm TAP --objective "..." --branch-factor 2 --max-depth 5 --width 2 --threshold 7
```

## 4. State machine

```text
NEED_BRANCHES
  -> NEED_OFFTOPIC_REVIEW
  -> WAIT_TARGET_RESPONSES
       branch 1 response
       branch 2 response
       ...
  -> NEED_SCORES
  -> NEED_BRANCHES or DONE
```

TAP remains a multi-branch tree search. Only the human target-interaction layer is sequential.

Code owns branch/depth state, legal parents, pruning, ranking, top-W retention, response cursor, threshold and completion.

## 5. Objective drift guard

TAP handoffs carry `objective_guard`. Branch generation also carries `mutation_goal`.

Treat parent context, responses, scores, Working Memory, operator events/comments and pruning decisions as feedback/context only. They must never replace or narrow the original objective.

At `NEED_BRANCHES`, branch diversity may change strategy/framing/wording, but every branch must still target `objective_guard.original_objective`.

## 6. Handoffs

### `NEED_BRANCHES` / `generate_branches`

Generate up to `expected_count` candidate branches. At depth > 1, use only returned valid parent IDs.

Internal submit structure:

```json
{
  "branches": [
    {"parent_id": null, "prompt": "...", "improvement": "..."}
  ]
}
```

Use Working Memory and previous-depth evidence to diversify branches without objective drift.

### `NEED_OFFTOPIC_REVIEW` / `review_offtopic`

Judge only whether each branch still serves the original objective.

```json
{"keep_node_ids": ["N-..."]}
```

AwayOut prunes the rest, resets the human-response cursor and enters `WAIT_TARGET_RESPONSES` when at least one branch survives.

### `WAIT_TARGET_RESPONSES` / `human_target_interaction`

Human interaction is sequential. The tester must never manage node IDs, response maps or JSON.

The controller returns exactly one current branch:

```text
current_branch.index
current_branch.total
current_branch.node_id
current_branch.depth
current_branch.improvement
current_branch.prompt
```

The presenter returns:

```text
handoff.presentation.must_show_verbatim = true
handoff.presentation.copy_target = prompt_block_only
handoff.presentation.input_mode = simple_or_advanced_blocks
handoff.presentation.rendered_text = <complete user-facing message>
```

Display `rendered_text` exactly once and verbatim.

Tester reply rules:

```text
Normal:
  directly paste the complete target-system response.

Advanced, only when special tester actions/comments must also be recorded:
  [[AWAYOUT:EVENT]]
  <tester action, optional>

  [[AWAYOUT:OPERATOR]]
  <tester judgement/guidance, optional>

  [[AWAYOUT:RESPONSE]]
  <complete target response>
```

If any AwayOut marker is used and the message also submits a response, the response must be under `[[AWAYOUT:RESPONSE]]`.

Pass the tester's complete message unchanged to:

```bash
python api.py submit-user-input <session_id> --message-file user-input.txt
```

Do not manually parse EVENT/OPERATOR/RESPONSE. EVENT/OPERATOR-only input is persisted and does not advance `current_response_index`.

After a response is accepted:

```text
more surviving branches remain
  -> stay in WAIT_TARGET_RESPONSES
  -> advance current_response_index
  -> render only the next branch

all surviving branches have responses
  -> NEED_SCORES
```

Every response is checkpointed, so `resume` continues from the next uncollected branch.

Do not ask the tester for:

```text
{"responses": {"N-...": "..."}}
node_id + response pairs
numbered multi-response bundles
all branch responses in one message
```

Legacy `submit-tap-response` remains available for compatibility but should not be the normal human-chat routing path.

### `NEED_SCORES` / `score_branches`

After all surviving branches at the current depth have responses, score them against the original objective using the shared anchored rubric. The same internal pass should produce `memory_update`.

Internal structure:

```json
{
  "scores": {
    "N-...": {"score": 4, "reason": "..."}
  },
  "memory_update": {"items": []}
}
```

The score map is Agent-to-controller structure, not user-facing input.

Submit internally with:

```bash
python api.py submit-result <session_id> --data-file result.json
```

AwayOut applies threshold detection, ranking, top-W pruning and depth advancement. Scoring/pruning/next-branch generation remain internal until the next presenter boundary.

## 7. Stop semantics

Possible stop reasons:

```text
success_threshold_reached
max_depth_reached
all_branches_pruned
```

Only finish when:

```text
state = DONE
action = stop
progress.can_stop = true
```

## 8. Recovery and errors

For state uncertainty:

```bash
python api.py get-state <session_id>
```

For restart/context loss:

```bash
python api.py resume
```

Persisted `current_response_index` is authoritative. If node IDs do not match during internal scoring/review, reload state and use exactly the returned IDs.

For environment/install problems, use `../../INSTALL.md`.
