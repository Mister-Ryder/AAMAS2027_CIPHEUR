# CIPHEUR：LLM 初始化与当前实例内演化（online v2）

本轮实现将 LLM 的职责从单一评分表达式扩展到**结构特征、排序规则、局部搜索政策与演化模板**。LLM 根据完整 TRAIN 求解失败反馈及真实结构见证离线生成可执行配方；正式求解时，优化器在当前完整实例内更新配方与参数，并由可信内核执行预算控制、可行性检查和收益接受。

这是一份代码和实验入口说明。方法解释、调用来源与尚未证实的结论见 [LLM参与扩展与方法边界](reports/LLM参与扩展与方法边界.md)；固定实验条件见 [PROTOCOL.md](PROTOCOL.md)。实验结果应进入独立报告，不能把下面的工程状态或局部诊断当成完整性能结论。

## 当前交付状态（2026-10-06）

| 项目 | 已完成或待完成内容 |
| --- | --- |
| 真实 LLM 合成 | 两轮共6次实际尝试、4次成功；首轮2次API拒绝保留。每轮Witness/Feedback各6条，共24条真实配方，按轮分开存放 |
| 离线调用成本 | 已知输入158,148 tokens、输出71,064 tokens；失败调用没有token记录，不补成零。请求模型 `gpt-6.1-sol`，实际服务模型不可观察，记为 `unknown` |
| 动态优化实现 | 当前实例内种群不超过4；支持特征、规则、系数及局部搜索政策变异；每次运行重置学习状态 |
| 工程检查 | 43项有意义的测试已通过；不等于完整调度优于对照方法 |
| 第一轮开发比较 | 16个TRAIN图×9方法×10 CPU秒×seed2＝144次；144/144完成，0失败 |
| 第二轮开发 | 12条真实修订配方与两份控制配置已实际执行；144/144完成，全部完整可行、0失败 |
| 两轮云端执行 | 两轮各144次，共288次真实开发运行；这是重复比较，不扩大独立样本量 |
| 正式比较 | 32个TEST图×9方法×10/30 CPU秒×seed2＝576次；未通过性能门，未启动，仍pending |
| 性能结论 | 第二轮Witness较首轮下降，低于同轮Fixed、Grammar、Degree及CHILS p1；新输出的参与已确认，效能优势未成立 |

状态是本说明撰写时的快照；最终完成量、失败量和代码版本以注册与结果记录为准。旧版被中止的TEST部分结果不纳入本轮分析，也不进入LLM输入或开发选优。

第一轮开发中，各方法16图等权平均完整调度收益（秒）为：Witness **735,924.746**、Grammar **737,427.769**、Degree **740,969.631**、CHILS p1 **750,236.537**；同Witness银行固定对照为 **732,513.106**。Witness平均每次运行feature CPU为 **3.021秒**，固定对照为 **7.990秒**。这些TRAIN结果说明动态版本相对固定对照有改善，同时尚未超过非LLM初始化及经典求解组件。特征CPU下降也不能单独归因LLM有效。这是开发结果，不能替代TEST泛化结论。

16图来自4配置×AU/AP×r000/r001；物理组与配置重复测量，不是16个独立样本。两组各8图，组内等权再组间等权与这里的16图均值一致。上述仅列收到的主要反馈，完整9方法、失败状态与成本应在独立结果报告中呈现。

第二轮已经完成，平均完整收益如下（相同16个TRAIN图、10 CPU秒预算、seed2；单位秒）：

| 方法 | 第二轮完整收益 |
| --- | ---: |
| LLM Witness | 733,079.886 |
| 同Witness银行Fixed | 733,971.760 |
| Grammar online | 735,645.231 |
| Degree | 741,458.532 |
| CHILS p1 | 750,236.537 |

Witness较首轮降低 **2,844.860秒，约0.387%**；特征CPU由 **3.021→6.074秒/job**，实际新增特征读取由 **32,284.500→70,082.125次/job**，第二轮包含父、子两方真实计算。读取和成本增加不证明有效性，也不能仅据两轮差推断哪个组件造成退步：配方、控制策略和共同执行器工程修正同时改变，这是整个系统迭代差。

全部9方法及不利结果见[第二轮完整比较](reports/development_round2/完整调度比较.md)、[两轮配对比较](reports/development_round2/两轮比较.md)和[原始汇总表](reports/development_round2/primary_table.csv)。第二轮配方和控制配置不升格为优势版本；正式576次保持pending，不自动启动。第二轮运行中的信息循环触发为0，不能声称已在部署求解中验证矛盾引导的表示修复。

第二轮真实LLM输入新增第一轮144次完整调度对比、实际controller源码、特征与搜索成本、真实曲线及失败诊断。输出除了每组6条修订配方，还包含信用度量、演化间隔、语义变异方式和parent–child race配置。两组实际输出一致选择 `absolute_signed_gain_per_cpu`、`evolve_every=32`、`bounded_relative`、`atomic_template`、`paired_race=true`，见各自[配置文件](configs_round2/)。这里的32指信用更新次数；竞赛中的父、子方案分别更新，不等于32个trial。

第二轮银行与控制配置已在完整云端求解中实际执行，但没有通过性能门；真实参与不等于效能证明。两轮结果及版本分别保存，正式576次仍pending，不混入第一轮银行、实现、调用成本或性能记录。

第二轮最初两次响应在旧numeric rule共用“48节点/depth8”限制下被排除，见[audit_round2.json](audit_round2.json)。在任何第二轮性能计算前，工程接口将纯数值排序规则独立限定为256语义节点、depth16、字符串长度2000；typed结构特征仍为48节点/depth8，安全表达式检查仍禁止属性访问、导入和任意代码执行。同两份原始响应经[修正后审计](audit_round2_interface_corrected.json)均接受，没有修改模型输出、人工补配方或新增调用。这是接口修正，不是LLM产生的性能收益；旧审计保留。

## 快速找到证据

| 路径 | 用途 |
| --- | --- |
| [PROTOCOL.md](PROTOCOL.md) | 数据划分、预算、9方法、统计单元和能力边界 |
| [schema.json](schema.json) | 声明式配方输出合同 |
| [context/train_failure_packet.json](context/train_failure_packet.json) | 只来自TRAIN的完整方法表现与运行诊断输入 |
| [analysis/structural_challenge.json](analysis/structural_challenge.json) | TRAIN结构见证与初始配方诊断；不是最终调度结果 |
| [llm_calls](llm_calls/) | 原始prompt、响应、事件、receipt、失败尝试；不删除被拒绝调用 |
| [audit.json](audit.json) | 调用来源、校验、模型可观察性与文件hash |
| [audit_round2.json](audit_round2.json) / [audit_round2_interface_corrected.json](audit_round2_interface_corrected.json) | 同两次真实第二轮调用在接口修正前后的审计，原始响应不变 |
| [banks/witness_operators.json](banks/witness_operators.json) | 真实LLM生成的6条Witness配方 |
| [banks/feedback_operators.json](banks/feedback_operators.json) | 真实LLM生成的6条Feedback配方 |
| [banks/grammar_operators.json](banks/grammar_operators.json) | 非LLM语法初始化对照，不冒称LLM输出 |
| [banks_round2](banks_round2/) / [configs_round2](configs_round2/) | 第二轮12条真实修订配方与LLM实际输出的控制配置 |
| [scripts/register_comparison.py](scripts/register_comparison.py) | 只检查元数据/hash并注册固定job，不自行启动云端运行 |
| [scripts/benchmark.py](scripts/benchmark.py) | 单次完整实例比较入口 |
| [scripts/run_queue.py](scripts/run_queue.py) | 固定job队列，保留失败与耗时，不覆盖已有输出 |
| [registrations](registrations/) | 源码、银行、图、元数据的冻结来源记录 |
| [cloud](cloud/) | 云端记录同步位置；开发/正式/旧版本必须分开统计 |
| [reports/development](reports/development/) / [reports/development_round2](reports/development_round2/) | 两轮完整开发结果，保留所有方法及负结果；第二轮另含两轮配对比较 |

## LLM怎样参与求解

首轮离线输入包含30行完整TRAIN方法/预算表现和24条同graph、同seed的真实运行曲线，同时提供feature CPU、throughput、原始拒绝情况、严格条件证书及实际结构见证。第二轮再加入刚完成的144次TRAIN比较、实际源码及成本/曲线/失败反馈，输出范围扩展到控制器配置。Witness与Feedback输入的差异以各自保存的prompt为准。两轮24条配方来自实际API响应，经schema和typed校验进入各自银行，不是代理手写代替。

每条配方声明：结构特征、排序表达式、patch锚点/删除量/范围/重构方法、4个系数、变异尺度和停滞响应。局部patch最多64个节点，超限拒绝，结构操作在当前残余图上执行。生成程序不能任意调用Python、LLM或优化oracle。

运行时从当前完整冲突图开始冷启动。种群、系数、incumbent、信用、证据archive、随机数状态与缓存均重置；控制器根据当前实例的候选收益和成本进行更新。初始配方可复用，其运行状态不跨TEST实例传递。源码与初始化银行固定，是为了可复现；它们不意味着每次求解使用历史TRAIN选出的不变评分头。

内核保留整数微秒权重，对完整可行调度计奖。LLM不负责宣称数学界可靠，也不决定非法调度是否可接受；条件界、数值计算、全图可行性与实际收益均由内核承担。在线证据、失败候选、特征与控制器计算都计入在线CPU预算，离线LLM成本另报。

第二轮按真实有符号增益/CPU更新信用，不按删除权重归一化；系数扰动围绕语义初始值限制范围与符号，原始零系数不能任意激活。`atomic_template`在当前实例内组合两份LLM原始评分块及相应特征，合法组合最多3个特征；不能组合时明确记录unavailable，不冒称表示修复。子方案首次实际执行可与父方案在相同F/P下竞赛，双方实际成本计费、双方原始有符号收益保留，收益接受与排序/共同exchange归属按实际赢家记录。当前表示archive的维度/语义校正及安全解释器修正属于共同工程实现，不能归为LLM独有贡献。

## 本轮比较范围

9方法为 `llm_witness`、`llm_feedback`、`grammar_online`、`witness_fixed`、`witness_base9`、`degree`、`chils_ils`、`chils`、`cp_sat`。CHILS使用原生[SEA2025发表实现](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.SEA.2025.22)，population1/4均单线程；CP-SAT为[CP2023介绍的求解器](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.CP.2023.3)，单worker。Degree是同内核经典组件，不称完整文献算法复现。

已注册的正式TEST计划为AU/AP的r008/r009，8配置覆盖均匀、异质及开发未用的配置。两轮开发未通过性能门，该576次计划未启动、仍pending。独立统计单元是r008/r009两组物理来源，32个配置图不是32个独立样本。主指标为完整可行调度时长，必须同时呈现实际CPU、墙钟、超额、失败和机制成本。曲线只画真实提交事件；CHILS缺少中间trace时不插值。

当前实现是**静态配置下重新求解**，没有warm state、求解中途约束事件或任务到达。新版公开算法数据集比较也尚未完成。所有这些边界应在结果报告和论文discussion中明确。

## 目前能说到哪一步

初始TRAIN P64结构诊断中，Witness有5/6配方产生区分，Feedback/Grammar各1/6；初始严格规则拟合Witness1/6，另两组0/6。这只说明特定见证下部分表达式具有区分能力，不能推出更好的排序、接受收益或完整调度质量。最终报告必须分别检查“表示区分→实际排序使用→候选接受→完整质量”，同时保留失败链条。

LLM程序演化、扩展输入/输出接口和预算内互补组合均已有正式文献。尤其[LACE（Nature Machine Intelligence，2026）](https://www.nature.com/articles/s42256-026-01307-8)与本轮扩展LLM输出和成本组合存在重合，不能将这些一般机制称为原创。拟检验的区别应落在认证矛盾与见证定向表示、以及当前实例内适应；区别的效果和原创边界仍需证据支持。
