from __future__ import annotations

from interactive_pair import run as run_pair

SEP = "=" * 72


def ask(prompt: str, default: str = "1") -> str:
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def main() -> None:
    print(SEP)
    print("AwayOut-AI · Unified Security Testing Entry")
    print("用于授权的 AI / Chatbot 安全测试")
    print(SEP)
    print("\n攻击算法:")
    print("  1. PAIR     - 反馈驱动的迭代优化（当前可用）")
    print("  2. TAP      - Tree of Attacks with Pruning（预留，待接入）")
    print("  3. DrAttack - Prompt Decomposition & Reconstruction（预留，待接入）")

    choice = ask("选择算法", "1").lower()

    if choice in {"1", "pair"}:
        run_pair()
        return

    if choice in {"2", "tap"}:
        print("\nTAP 当前为预留算法入口，尚未接入可运行实现。")
        print("后续将用于多分支生成、评分、剪枝和攻击树扩展。")
        return

    if choice in {"3", "drattack", "dr"}:
        print("\nDrAttack 当前为预留算法入口，尚未接入可运行实现。")
        print("后续将用于 Prompt 分解、语义替换与重构流程。")
        return

    print("\n输入无效。当前默认运行 PAIR。")
    run_pair()


if __name__ == "__main__":
    main()
