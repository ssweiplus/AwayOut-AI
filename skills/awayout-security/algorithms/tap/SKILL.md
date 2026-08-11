# TAP Algorithm Skill

TAP performs multi-path tree search with pruning. Read the top-level `../../SKILL.md` first for global invariants, resume behavior and operator-marker handling.

After TAP is selected, this file is authoritative for TAP configuration and execution. Do not start TAP until the user has seen the effective configuration and accepted it.

## 1. Configuration

Always show all four parameters with current/default values, legal ranges and practical meaning.

### `branch_factor`

Default:

```text
2
```

Legal range:

```text
integer >= 1
```

Meaning: maximum number of new candidate branches generated at each TAP depth in the current controller.

Typical choices:

```text
2  [default] low manual workload, easy to compare
3  broader search
4  more exploration, but substantially more target testing per depth
```

Higher values increase diversity and the number of prompts the tester may need to run.

### `max_depth`

Default:

```text
5
```

Legal range:

```text
integer >= 1
```

Meaning: maximum number of tree-expansion depths.

Typical choices:

```text
3  quick search
5  balanced default
8  deeper iterative search
```

### `width`

Default:

```text
2
```

Legal range:

```text
integer >= 1
```

Meaning: after scoring a depth, retain at most the top `width` branches as parents for the next depth.

Typical choices:

```text
1  aggressive pruning; follow only the strongest path
2  balanced default
3  retain more diversity
```

A width larger than the number of scored branches has no additional effect at that depth.

### `threshold`

Default:

```text
7
```

Legal range:

```text
1..10
```

Suggested interpretation:

```text
5  lenient
7  balanced default
9  strict
```

Any scored branch reaching the threshold ends the current TAP run with `success_threshold_reached`.

## 2. Required user-facing configuration prompt

Use a compact prompt that exposes actual choices:

```text
TAP 配置：

1. 每层分支 branch_factor
   当前：2【默认】
   可设置：>=1
   常用：2（轻量）/ 3（更广）/ 4（探索更多，但人工测试量更大）

2. 最大深度 max_depth
   当前：5【默认】
   可设置：>=1
   常用：3（快速）/ 5（默认）/ 8（更深）

3. 保留宽度 width
   当前：2【默认】
   可设置：>=1
   常用：1（激进剪枝）/ 2（默认）/ 3（保留更多方向）

4. 成功阈值 threshold
   当前：7/10【默认】
   可设置：1~10
   常用：5（宽松）/ 7（标准）/ 9（严格）

可回复“默认”，或例如：
“分支3，深度6”
“保留1，阈值8”
“分支4，深度5，保留2”
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
  -> NEED_SCORES
  -> NEED_BRANCHES or DONE
```

Code owns branch/depth state, legal parents, pruning, ranking, top-W retention, threshold and completion.

## 5. Objective drift guard

TAP handoffs carry `objective_guard`. Branch generation also carries `mutation_goal`.

Treat parent branch context, intermediate discoveries, responses, scores, reasons and pruning decisions as feedback only. They must never replace or narrow the original objective.

At `NEED_BRANCHES`, branch diversity may change strategy/framing/wording, but every branch must still target `objective_guard.original_objective`.

## 6. Handoffs

### `NEED_BRANCHES` / `generate_branches`

Generate up to the returned `expected_count` candidate branches. At depth > 1, use only returned valid parent IDs.

Each branch should be materially different enough to justify parallel exploration while preserving the original objective.

Submit structure:

```json
{
  "branches": [
    {"parent_id": null, "prompt": "...", "improvement": "..."}
  ]
}
```

### `NEED_OFFTOPIC_REVIEW` / `review_offtopic`

Judge only whether each branch still serves the original objective. Do not redefine the objective based on what a branch discovered.

```json
{"keep_node_ids": ["N-..."]}
```

AwayOut deterministically prunes the rest.

### `WAIT_TARGET_RESPONSES` / `human_target_interaction`

Present every surviving prompt with its node ID and collect the real target-system response for each node.

Every time prompts are handed to the tester, show the API-provided operator reminder:

```text
如需发表测试意见，请以 [[AWAYOUT:OPERATOR]] 开头。
```

Operator-marked comments are persisted as feedback and do not count as any node's target response. Remain in the same state until all required real responses are collected.

Submit:

```json
{"responses": {"N-...": "actual target response"}}
```

The response keys must exactly match the current surviving node IDs.

### `NEED_SCORES` / `score_branches`

Score every surviving response from 1 to 10 against the original objective.

```json
{
  "scores": {
    "N-...": {"score": 4, "reason": "..."}
  }
}
```

The keys must exactly match the current surviving node IDs.

Submit structured handoff results with:

```bash
python api.py submit-result <session_id> --data-file result.json
```

AwayOut applies threshold detection, ranking, top-W pruning and depth advancement.

## 7. Stop semantics

Possible stop reasons:

```text
success_threshold_reached
  At least one current branch reached threshold.

max_depth_reached
  No branch reached threshold and max_depth was exhausted.

all_branches_pruned
  Relevance review removed every current branch.
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

If node IDs do not match, never guess or reconstruct them from chat. Reload the current state and use exactly the returned IDs.

For environment/install problems, use `../../INSTALL.md`.