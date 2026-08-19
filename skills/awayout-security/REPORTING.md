# 测试记录归档规范

## 1. 定位

本规范用于指导 AwayOut 如何记录每一次测试的完整过程。

所有测试记录统一归档至：

```text
test-report-{会话ID}/
```

完整原文永久保留，供后续复盘、审计、知识沉淀使用。

## 2. 核心原则

**一切皆完整记录。**

- 成功轮次：完整保留
- 失败轮次：完整保留
- 揭示防御机制的轮次：完整保留
- 重复失败模式：完整保留
- 操作员干预：完整保留

宁可记录过多，不可记录过少。Working Memory、摘要和分析文档都只是索引/压缩层，永远不能替代 Prompt 和目标系统响应原文。

## 3. 目录结构

```text
test-report-{会话ID}/
├── SUMMARY.md
├── ATTACK_PATTERN.md
├── TURNING_POINTS.md
├── prompt-tree.md
├── strategy-evolution.md
└── RESPONSES/
    ├── round01.md
    ├── round02.md
    ├── round03.md
    └── ...
```

`common/report.py` 由 `AgentSessionStore.save()` 自动调用并持续刷新这些文档。测试中断时也应保留已经完成的原文和当前状态。

## 4. 必填元数据

```markdown
## 测试元数据
- 会话 ID：
- 测试目标：
- 目标系统：
- 算法：
- 配置：
- 测试时间：
- 测试时长：
- 最佳评分：
- 成功尝试数：
- 最终状态：（DONE / 中断）

## 测试结果
- 状态：（成功 / 失败 / 进行中）
- 评分趋势：[]

## 关键发现（3-5条）
1.

## 防御建议（2-4条）
1.
```

目标系统存放在 session `_runtime.metadata.target_system`。若启动时已知，Host Agent 应内部执行：

```bash
python -m common.memory metadata <session_id> --target-system "<target>"
```

未知时不得猜测，可暂记“未填写”。

## 5. 每轮记录格式

每轮统一使用：

```markdown
# Round X

## 元数据
| 字段 | 值 |
|------|-----|
| 轮次 | X/N |
| 策略 | [策略名称] |
| 评分 | X/10 |
| 状态 | ✅ 成功 / ❌ 未达标 / ⏳ 未评分 |
| 操作员反馈 | [原文 + 可用的时机元数据] |

## Prompt
```text
[完整 Prompt 原文]
```

## 目标系统响应
```text
[完整响应原文]
```

## 评分理由
[证据化评分依据]

## 关联分析
- 与前几轮的关联：
- 对后续测试的影响：
- 操作员反馈的作用：
```

其中 Prompt/Response 必须直接来自持久化 controller/session 数据，不允许通过 LLM 摘要后再写档。

## 6. 关键转折点判定

以下任一情况必须记录：

| 条件 | 说明 |
|------|------|
| 评分首次达标 | 达到或超过 threshold |
| 评分首次满分 | 达到 10/10 |
| 评分变化 ≥ 3 | 相邻有效评分大幅波动 |
| 策略重大切换 | 策略标签发生显著变化 |
| 操作员反馈影响结果 | 外部情报改变后续方向 |
| 目标防御方式变化 | 从拒绝转部分回答或反向变化 |

自动归档器确定性识别能够从持久化数据判断的条件；需要语义判断的条件必须基于真实轮次证据和 Working Memory，不得凭空补写。

## 7. ATTACK_PATTERN.md

至少覆盖：

- 攻击/测试阶段划分
- 核心决定性链路
- 策略组合有效性
- 操作员反馈作用

自动生成部分只写能从节点、评分、策略和反馈确定的内容；高级阶段命名和因果结论应由最终复盘基于归档证据补充。

## 8. prompt-tree.md

每个节点应尽可能包含：

- 轮次/节点
- 策略或变异方向
- Prompt 摘要
- 评分
- 简要结果状态

同时保留评分趋势和关键路径入口。

## 9. strategy-evolution.md

记录：

- 策略切换时间线
- 切换前后策略
- 持久化评分理由/人工反馈所能支持的原因
- 各策略真实效果

不得根据策略名称自动臆测“最佳场景”。

## 10. 文档间链接

- `SUMMARY.md` → 所有轮次 + 分析文档
- `ATTACK_PATTERN.md` → `TURNING_POINTS.md`
- `TURNING_POINTS.md` → 对应 `RESPONSES/roundXX.md`
- `prompt-tree.md` → `ATTACK_PATTERN.md` / `TURNING_POINTS.md`
- 每轮 → `SUMMARY.md` / `prompt-tree.md`

## 11. 质量检查

- [ ] Prompt 原文完整
- [ ] 目标系统响应完整
- [ ] 评分理由有具体证据和剩余缺口
- [ ] 策略名称/节点关系正确
- [ ] 操作员反馈原文保留
- [ ] 精确标识符未被摘要改写
- [ ] Working Memory 不替代原文
- [ ] 超链接指向正确
- [ ] 中断状态仍已落盘
