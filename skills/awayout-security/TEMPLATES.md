# PyRIT 模板软引导与高分经验传递

本功能属于 Agent Mode（skills/awayout-security），不依赖旧版 awayout/seeds.py，不需要运行 PyRIT 框架。只在有授权的目标系统上使用。

## 1. 导入 PyRIT 提示词模板

在本地获取 PyRIT 仓库后，安装导入器的可选依赖：

    python -m pip install pyyaml

    cd skills/awayout-security
    python api.py --store .awayout-agent import-pyrit --source /path/to/PyRIT/pyrit/datasets/jailbreak/templates
    python api.py --store .awayout-agent list-templates

导入结果保存在 .awayout-agent/templates/pyrit.json，不进入源码库。
源模板的 name、作者、源链接与源文件位置都会保留。导入仅接受文本型 YAML 和简单的 {{ prompt }} / {{ objective }} 变量，不执行任意 Jinja 表达式。跳过不兼容的模板并报告数量。

注意：PyRIT 的 YAML 文件通常不含一一对应的 8 类官方分类字段。AwayOut 的分类是建议性映射；来源文件没有分类时，少数已知模板使用建议分类，其余标记为 unclassified，不要把推断标签当成官方事实。导入后请检查原始模板来源及许可证。

## 2. 开始测试

    python api.py --store .awayout-agent start-test --algorithm PAIR --objective "经授权的具体测试目标" --template-mode auto --template-limit 3

template-mode 可取：
- auto：攻击 LLM 可借鉴、改写、组合或忽略参考模板（默认）
- reference：借鉴模板（保留自主生成空间）
- rewrite：借鉴其技战术，重写表达
- combine：组合多条模板思路
- skip：不使用模板；仍可参考已评分历史节点

template-limit 只控制每次交给生成器的参考数量（1～3），不是强制使用数量。原有算法、阈值、评分、剪枝及停止机制不变。配置保存在会话中，断点恢复时继续生效。

## 3. 生成结果附加 template_use 标记

要区分配置模式（mode）与本轮实际动作（action）。auto 不能作为已执行动作上报。标记为可选字段，以兼容旧版客户端；新集成的 Host Agent 应主动上报。未报告的历史节点记为 unreported，不臆测模板使用情况。

PAIR 推荐使用 submit-result：

    {
      "prompt": "本轮生成的完整测试 Prompt",
      "strategy": "logical_appeal",
      "template_use": {
        "action": "combine",
        "template_ids": ["pyrit:<导入后生成的模板ID>"],
        "experience_ids": ["N-上一轮节点ID"]
      }
    }

也可继续使用 submit-candidate --prompt-file ...，附加 --template-action、--template-ids、--experience-ids 参数。

TAP：在 submit-result 的 branches 数组中的每个分支上各自提供 template_use；它们按新生成的节点 ID 持久化。不要求每个分支使用同一种模板，避免分支同质化。

DrAttack：基线阶段使用顶层 template_use；重构阶段使用 template_uses 对象，以策略名称（如 icl_structured）为键分别上报实际动作。语义拆解步骤本身不记录虚构的模板使用。

标准标记：
- action：reference / rewrite / combine / skip
- template_ids：实际使用的模板 ID 数组；skip 时必须为空
- experience_ids：实际参考的高分节点 ID 数组

字段值会进行校验；未知模板 ID、错误动作、与固定 mode 冲突等会报错。模板缺失时，旧式不带标记的生成命令仍然可用。

## 4. 高分经验自动传递

每次进入生成状态，handoff.template_guidance 包含：
- recommended_templates：至多 3 个候选参考模板；可被 LLM 忽略
- elite_experiences：当前会话内真实已评分节点的前 3 名（包含评分、评分理由、真实目标响应片段、参考的模板动作）
- instruction、submission_contract：告知 Host Agent 如何使用及记录

高分节点来自 PAIR/TAP/DrAttack 已持久化的数据，自动复用评分，不需要重写原有评分器。仅根据 LLM 评分排序；这不等于独立验证的攻击成功，也不能断言模板造成了高分。完整 Prompt/Response 原文仍由原有会话文件与测试报告保存，handoff 只给出截断摘要。

当前 Elite Memory 为会话内高分经验，不跨任务迁移，也不引入额外模型调用。之后若要实现跨任务经验库，可增加目标类型、环境特征和证据置信度，避免跨场景机械复制。

## 5. 代码边界

新增：
- common/template_guidance.py：导入、推荐映射、使用标记校验、Elite Memory

修改：
- api.py：导入/列表命令、会话配置、各算法的生成 handoff 与实际使用上报
- common/store.py：持久化 template_config 和 template_uses

兼容原有会话：没有模板配置时默认 auto；没有模板库时不注入虚构模板；不改变旧的 submit-result 必填字段。
