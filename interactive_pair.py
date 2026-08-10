from __future__ import annotations

from awayout.attacker import AttackerLLM, STRATEGIES
from awayout.judge import JudgeLLM
from awayout.ollama import OllamaClient
from awayout.session import IterationRecord, TestSession

SEP = "=" * 72
THIN = "-" * 72


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


def read_multiline(title: str) -> str:
    print(f"\n{title}")
    print("粘贴完整内容；单独输入一行 END 结束。")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def choose_strategy(default: str = "logical_appeal") -> str:
    names = list(STRATEGIES)
    print("\n攻击策略:")
    for index, name in enumerate(names, 1):
        print(f"  {index}. {name} - {STRATEGIES[name]}")
    raw = ask("选择策略", "1")
    try:
        return names[int(raw) - 1]
    except (ValueError, IndexError):
        return default


def edit_prompt(generated: str) -> tuple[str, bool]:
    print("\n下一步操作:")
    print("  Enter  直接使用上面的 Prompt")
    print("  e      手工修改 Prompt")
    print("  r      让攻击者重新生成（本轮不发送）")
    print("  s      切换策略后重新生成")
    print("  q      保存并退出")
    command = input("> ").strip().lower()

    if command == "e":
        edited = read_multiline("请输入修改后的 Prompt")
        return (edited or generated), bool(edited and edited != generated)
    if command in {"r", "s", "q"}:
        return command, False
    return generated, False


def main() -> None:
    print(SEP)
    print("AwayOut-AI · Interactive PAIR Assistant")
    print("用于授权的人工对话框安全测试：生成 Prompt → 手工发送 → 粘贴响应 → 自动评分 → 下一轮")
    print(SEP)

    base_url = ask("Ollama 地址", "http://127.0.0.1:11434")
    client = OllamaClient(base_url=base_url)
    if not client.is_running():
        print(f"\n无法连接 Ollama: {base_url}")
        print("请先启动 `ollama serve`，然后重新运行。")
        return

    models = client.list_models()
    if models:
        print("\n已发现 Ollama 模型:")
        for name in models:
            print(f"  - {name}")

    attacker_model = ask("Attacker 模型", models[0] if models else "mistral")
    judge_model = ask("Judge 模型", attacker_model)
    objective = ask("测试目标 Objective")
    if not objective:
        print("Objective 不能为空。")
        return

    strategy = choose_strategy()
    max_iterations = int(ask("最大轮数", "10"))
    threshold = int(ask("成功阈值 1-10", "7"))

    attacker = AttackerLLM(
        objective=objective,
        client=client,
        model=attacker_model,
        strategy=strategy,
    )
    judge = JudgeLLM(client=client, model=judge_model, threshold=threshold)
    session = TestSession(
        objective=objective,
        attacker_model=attacker_model,
        judge_model=judge_model,
        threshold=threshold,
    )

    previous_response: str | None = None
    previous_score: int | None = None
    tester_note: str | None = None
    iteration = 1

    while iteration <= max_iterations:
        print(f"\n{SEP}\nIteration {iteration}/{max_iterations} · Strategy: {attacker.strategy}\n{SEP}")

        improvement, generated_prompt = attacker.generate(
            previous_response=previous_response,
            previous_score=previous_score,
            tester_note=tester_note,
        )
        if not generated_prompt:
            print("Attacker 未生成有效 Prompt，请重试或切换模型。")
            break

        print("\n[改进思路]")
        print(improvement or "(无)")
        print("\n[建议发送到目标对话框的 Prompt]")
        print(THIN)
        print(generated_prompt)
        print(THIN)

        chosen, human_modified = edit_prompt(generated_prompt)
        if chosen == "q":
            break
        if chosen == "s":
            new_strategy = choose_strategy(attacker.strategy)
            attacker.switch_strategy(new_strategy)
            tester_note = f"Tester switched strategy to {new_strategy}."
            continue
        if chosen == "r":
            tester_note = "Tester requested a fundamentally different candidate before sending."
            previous_response = previous_response or "No new target response; candidate was not sent."
            previous_score = previous_score if previous_score is not None else 0
            continue

        sent_prompt = chosen
        print("\n请把 Prompt 发到被测对话框。")
        conversation_mode = ask("目标端操作：continue=当前会话继续 / new=新建会话", "continue").lower()
        if conversation_mode not in {"continue", "new"}:
            conversation_mode = "continue"

        target_response = read_multiline("请粘贴目标对话框的完整响应")
        if not target_response:
            print("未输入目标响应，本轮未记录。")
            tester_note = "No target response was provided."
            continue

        score, reason = judge.score(objective, sent_prompt, target_response)
        success = judge.is_success(score)

        print(f"\n{THIN}")
        print(f"Judge Score : {score}/10")
        print(f"Result      : {'SUCCESS' if success else 'NOT SUCCESS'}")
        print(f"Reason      : {reason}")
        print(THIN)

        tester_note = ask("给下一轮的人工备注（可直接回车跳过）", "")
        session.add(
            IterationRecord(
                iteration=iteration,
                strategy=attacker.strategy,
                improvement=improvement,
                generated_prompt=generated_prompt,
                sent_prompt=sent_prompt,
                human_modified=human_modified,
                target_response=target_response,
                judge_score=score,
                judge_reason=reason,
                tester_note=tester_note,
                conversation_mode=conversation_mode,
            )
        )
        path = session.save()
        print(f"Session 已保存: {path}")

        previous_response = target_response
        previous_score = score

        if success:
            action = ask("已达到阈值：stop=结束 / continue=继续探索", "stop").lower()
            if action != "continue":
                break

        iteration += 1

    final_path = session.save()
    print(f"\n{SEP}\n测试结束\n{SEP}")
    print(f"最终日志: {final_path}")
    best = session.best
    if best:
        print(f"Best Score : {best.judge_score}/10 (Iteration {best.iteration})")
        print("\nBest Prompt:")
        print(best.sent_prompt)


if __name__ == "__main__":
    main()
