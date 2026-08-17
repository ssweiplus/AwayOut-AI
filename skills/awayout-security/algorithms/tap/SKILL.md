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
4  more exploration
```

Higher values increase branch diversity. Human target testing remains sequential: the tester sees one branch Prompt at a time rather than all branches at once.

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
   常用：2（轻量）/ 3（更广）/ 4（探索更多）
   说明：即使有多个分支，人工测试时仍一次只展示 1 个 Prompt。

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

Treat parent branch context, intermediate discoveries, responses, scores, reasons and pruning decisions as feedback only. They must never replace or narrow the original objective.

At `NEED_BRANCHES`, branch diversity may change strategy/framing/wording, but every branch must still target `objective_guard.original_objective`.

## 6. Handoffs

### `NEED_BRANCHES` / `generate_branches`

Generate up to the returned `expected_count` candidate branches. At depth > 1, use only returned valid parent IDs.

Each branch should be materially different enough to justify parallel exploration while preserving the original objective.

Internal submit structure:

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

AwayOut deterministically prunes the rest, resets the human-response cursor and enters `WAIT_TARGET_RESPONSES` when at least one branch survives.

### `WAIT_TARGET_RESPONSES` / `human_target_interaction`

Human interaction is sequential. The user must never be asked to manage the branch-response map, node IDs, or JSON.

For every step, the controller returns exactly one current branch:

```text
current_branch.index
current_branch.total
current_branch.node_id
current_branch.depth
current_branch.improvement
current_branch.prompt
```

`../../common/presenter.py` renders this as the mandatory user-facing message:

```text
handoff.presentation.format = markdown
handoff.presentation.must_show_verbatim = true
handoff.presentation.copy_target = prompt_block_only
handoff.presentation.input_mode = single_plain_text_response
handoff.presentation.rendered_text = <complete current-branch message>
```

The host Agent MUST display `handoff.presentation.rendered_text` exactly once and verbatim, then wait for one unmarked user message containing only the current target-system response.

Typical layout:

````markdown
## TAP 深度 2/5 · 分支测试 1/2

### 当前分支
- 分支：`N-...`
- 说明：本次只测试这一条；提交响应后会自动进入当前深度的下一个存活分支。
- 变异方向：...

### 当前人工意见
暂无。

---

### 请只复制下面的 Prompt

```text
<当前唯一需要测试的 Prompt>
```

---

### 下一步
1. 只复制上面的 Prompt 到目标系统。
2. 将这一次的实际响应直接粘贴回来。
3. 不需要填写 JSON，也不需要填写 node_id。
4. 当前深度所有存活分支响应收集完成后，才进入统一评分和剪枝。
````

Use:

```bash
python api.py submit-tap-response <session_id> --response "<actual target response>"
```

For multiline content:

```bash
python api.py submit-tap-response <session_id> --response-file response.txt
```

After one response is persisted:

```text
more surviving branches remain
  -> stay in WAIT_TARGET_RESPONSES
  -> advance current_response_index
  -> render only the next branch

all surviving branches have responses
  -> NEED_SCORES
```

Every single response is checkpointed, so `resume` continues from the next uncollected branch after interruption.

Do not ask the user for any of these:

```text
{"responses": {"N-...": "..."}}
node_id + response pairs
numbered multi-response bundles
all surviving branch responses in one message
```

Operator-marked comments remain feedback only and do not advance the branch cursor.

### `NEED_SCORES` / `score_branches`

After all surviving branches at the current depth have real responses, score every surviving response from 1 to 10 against the original objective.

Internal structure:

```json
{
  "scores": {
    "N-...": {"score": 4, "reason": "..."}
  }
}
```

The keys must exactly match the current surviving node IDs. This is Agent-to-controller structure, not user-facing input.

Submit internal structured handoff results with:

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

Persisted `current_response_index` is authoritative for which branch is currently waiting for a response. Do not infer it from chat history.

If node IDs do not match during internal scoring/review, never guess or reconstruct them from chat. Reload the current state and use exactly the returned IDs.

For environment/install problems, use `../../INSTALL.md`.
