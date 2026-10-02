# CIP-Heur：第二篇基础框架 v0.1

目标：实现 **LLM-Guided Graph Heuristic Synthesis via Constraint-Induced Preference Reversals** 的摘要方法链。当前交付是可运行的研究底座和完整性检查，尚未进行论文效果实验，也没有声称比 DRAGON 更优。

## 直接运行

在本文件夹打开 PowerShell，执行：

```powershell
.\run_smoke.ps1 -Check
```

或使用 Python 3.10+：

```powershell
python -m cipheur preflight --config configs/smoke.json
python -m cipheur run --config configs/smoke.json
python -m unittest discover -s tests -q
```

默认流程只需 Python 标准库，不需要 GPU、训练模型、安装 OpenAI SDK 或 API 密钥。结果进入 `output/run_时间戳/`，已有运行目录不覆盖。

第一份运行记录见 `baselines/foundation_v0.1.0/synthetic/summary.json`，旧底座适配运行见 `baselines/foundation_v0.1.0/v51_adapter/summary.json`。二者分别验证人工反转流程和真实数据接口；都不能作为性能结论。

## 实际执行的链路

1. 建立两套节点、权重、时间窗相同的冲突图，只改变一个合法的资源切换间隔。
2. 搜索两侧都可行且互相竞争的动作对，优先查询当前程序没有响应的约束变化。
3. 固定动作和既有边界承诺，计算四个条件完成问题的有效下界、上界和可行完成见证。
4. 只有严格上下界确认两侧偏好反转，才生成两条程序行为要求。
5. 用紧凑证据、当前程序、已有失败反馈生成或修订评分表达式。
6. 受限表达式通过语法检查后，回放全部累计要求，评估完整训练/验证调度；满足要求的候选才有资格替换当前程序。
7. 冻结程序，由固定 MWIS 可行构造器运行。调度入口不调用模型。

默认评分候选由本次助手编写，位于 `examples/assistant_seed_program.json`，运行时回放它。示例程序 `weight - 1.2 * conflict_weight` 只是用于贯通机制的种子，不是论文最终算法，也不是一次真实 API 合成实验。运行记录明确显示 `live_llm_calls=0`。

## LLM 如何参与

当前助手已经参与方法设计、程序编写和证据检查。持续自动合成通过独立提供方接口调用模型，不能把当前聊天会话直接当成本地 Python 模型服务。

建议先采用 **离线合成、模型可换、在线只执行程序**：用较小代码能力模型生成候选，以求解器证据和自动回放作筛选。更强模型是否值得使用，应以后续同证据、同调用/令牌预算的对照决定。

`configs/openai_small.json` 提供 `gpt-5.4-mini-2026-03-17` 的 Responses 接口配置；仅在已设置 `OPENAI_API_KEY` 的环境中手动运行：

```powershell
python -m cipheur run --config configs/openai_small.json
```

本次没有发起真实 API 调用。密钥仅从环境读取，不写入文件。模型拒绝、传输失败、未完成响应明确报错并保留可审计材料；非法评分程序明确拒绝，并把失败送入下一轮修订。没有静默模型回退。

文档依据：[官方模型页](https://developers.openai.com/api/docs/models/gpt-5.4-mini)、[结构化输出说明](https://developers.openai.com/api/docs/guides/structured-outputs)。模型选择可改配置，方法不依赖指定模型。依用户最新要求，本轮不接 DeepSeek harness。

## 旧底座复用

```powershell
.\run_smoke.ps1 -V51
```

这一入口需要 NumPy；当前本地 Python 已具备。读取原稳定包的 `data.py`、`graph.py`、`verifier.py`，保留其特殊卫星交叉规则，记录源文件和 C3 哈希。原包不修改，默认只取前 32 个节点作接口检查。

该小前缀在地面站间隔 340→500 时没有改变图边，因此没有反转证据。`paired_signal_available=false` 如实记录这个事实。人工示例采用独立的单容量时间冲突模型，不能混称与 V51 全部语义等价。

## 文件安排

| 路径 | 内容 |
|---|---|
| `cipheur/model.py` | 节点/图合同、合法约束干预、单容量示例 |
| `cipheur/oracle.py` | 预算化分支定界、固定边界、渐进区域与四界证据 |
| `cipheur/acquisition.py` | 当前程序驱动的查询排序、失败/无证据查询成本 |
| `cipheur/programs.py` | 可检查的评分语言、成对要求回放、固定可行构造器 |
| `cipheur/providers.py` | 回放、Responses、兼容 API 和可选外部命令合同 |
| `cipheur/pipeline.py` | 合成循环、拒绝反馈、候选归档、快照和哈希收据 |
| `cipheur/v51_adapter.py` | 原稳定底座的只读适配 |
| `configs/` | 运行/模型/预算配置 |
| `tests/` | 数值界、穷举对照、可行性、提供方与适配完整性检查 |
| `docs/DRAGON_REVIEW.md` | 参考论文 9 页详细研究与方法定位 |
| `docs/METHOD_CONTRACT.md` | 摘要逐项实现合同、证据范围和创新重点 |
| `docs/ROADMAP.md` | 下一阶段实现与正式实验计划 |
| `paper/ABSTRACT_TARGET.md` | 引用会话的最新摘要目标 |
| `manifest/FOUNDATION_STATUS.json` | 已验证范围、来源与当前里程碑 |

单次运行保留配置、图、证据、所有查询、提示/响应、候选与拒绝原因、完整调度、程序、源码快照和哈希收据。提供 `schedule` 子命令，可单独用已冻结程序运行一个导出的图。

```powershell
python -m cipheur schedule --graph examples/deployment_graph.json --program examples/assistant_seed_program.json --output output/deployment_check.json
```

## 当前边界

底座已实现三项机制的可运行接口及小规模正确性验证。当前主动获取是在给定合法干预池里排序查询，尚未实现大规模连续参数搜索；局部外部上界偏松时宁可无证据。未来要扩大干预与残余状态生成器、提高证据提取效率，并进行真实 LLM 自动修订和未见约束组合测试。不能把这些后续工作表述为已完成，也不能把示例分数写进论文结果。

## 代码仓库

第二篇独立仓库：[Mister-Ryder/AAMAS2027_CIPHEUR](https://github.com/Mister-Ryder/AAMAS2027_CIPHEUR)。首版冻结标签为 oundation-v0.1.0，日常开发使用 main。仓库设置、自动检查范围和版本管理约定见 docs/REPOSITORY.md。
