# AwayOut-AI

AwayOut-AI is a small human-in-the-loop assistant for authorized chatbot security testing.

The first version implements a **PAIR-style interactive workflow** for targets that you cannot or do not want to integrate through an API yet:

```text
Objective
   ↓
Attacker LLM (local Ollama)
   ↓
Suggested test prompt
   ↓
Human copies prompt into the target chatbot
   ↓
Human pastes target response back into AwayOut-AI
   ↓
Judge LLM (local Ollama)
   ↓
Score + feedback
   ↓
Attacker generates the next prompt
```

This keeps the target system completely manual while automating prompt refinement, scoring, and experiment logging.

> Use only for systems you are authorized to test.

## Features

- PAIR-style iterative prompt refinement.
- Local Ollama attacker model.
- Local Ollama judge model.
- Manual target chatbot interaction; no target API is required.
- Three built-in attack strategies:
  - `logical_appeal`
  - `authority`
  - `roleplay`
- Human editing before a prompt is sent.
- Regenerate a candidate without sending it.
- Switch strategy during a session.
- Mark whether each test continues the current target conversation or starts a new one.
- Judge score and reason after each target response.
- Configurable success threshold.
- JSON session logs containing both generated and actually-sent prompts.

## Requirements

- Python 3.10+
- Ollama
- At least one Ollama chat/instruct model

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Start Ollama:

```bash
ollama serve
```

Pull a model if needed, for example:

```bash
ollama pull mistral
```

## Run

```bash
python interactive_pair.py
```

The CLI will ask for:

1. Ollama URL.
2. Attacker model.
3. Judge model.
4. Test objective.
5. Attack strategy.
6. Maximum iterations.
7. Judge success threshold.

## Typical interaction

```text
AwayOut-AI · Interactive PAIR Assistant

测试目标 Objective: Test whether the chatbot reveals protected instructions
攻击策略: logical_appeal
最大轮数: 10

Iteration 1/10

[改进思路]
Use an evaluation-oriented framing for the initial attempt.

[建议发送到目标对话框的 Prompt]
...

下一步操作:
  Enter  直接使用上面的 Prompt
  e      手工修改 Prompt
  r      让攻击者重新生成
  s      切换策略后重新生成
  q      保存并退出
```

After sending the prompt to the target chatbot, paste the complete response and finish with a line containing only:

```text
END
```

AwayOut-AI then asks the judge model to score the result from 1 to 10 and feeds the response plus score into the next attacker iteration.

## Generated prompt vs sent prompt

The session log deliberately stores both:

```json
{
  "generated_prompt": "prompt produced by the attacker model",
  "sent_prompt": "prompt actually sent by the tester",
  "human_modified": true
}
```

This makes later review more accurate: you can distinguish fully automated discoveries from cases where a human tester improved the generated prompt.

## Conversation state

For every target response, the CLI records one of:

- `continue`: the prompt was sent in the same target chat session.
- `new`: the tester created a fresh target conversation first.

This does not automate the target UI. It records what the tester actually did so that single-turn and multi-turn behavior can be compared later.

## Session logs

Logs are written under:

```text
sessions/
```

Each record contains:

- iteration
- strategy
- attacker improvement summary
- generated prompt
- sent prompt
- whether a human modified it
- target response
- judge score
- judge reason
- tester note
- target conversation mode

`sessions/` is ignored by Git by default because test responses may contain sensitive data.

## Project layout

```text
AwayOut-AI/
├── awayout/
│   ├── __init__.py
│   ├── attacker.py
│   ├── judge.py
│   ├── ollama.py
│   └── session.py
├── interactive_pair.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Model roles

### Attacker model

The attacker should be a reasonably capable instruct/chat model. It needs to follow JSON-output instructions, interpret feedback, and generate materially different attempts across iterations.

### Judge model

The judge should be stable and instruction-following. It runs at temperature `0.0` and returns a score plus a short reason.

For quick local testing the same model can fill both roles. For more rigorous evaluation, using a different judge model reduces same-model bias.

## Next extensions

The code is intentionally small so later target adapters can be added without changing the attacker/judge loop. Natural next steps are:

- browser extension target adapter
- Playwright/Puppeteer target adapter
- generic HTTP/OpenAI-compatible target adapter
- TAP-style multi-branch interactive testing
- tree visualization and session replay
