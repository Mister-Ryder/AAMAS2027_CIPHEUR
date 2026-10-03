# 两篇 AAMAS 调度论文：同一研究标准下的比较

审查日期：2026-10-03。第一篇聊天已重新读取：`01a0fd53-e8f8-7bd0-9748-6173e09dc982`，host `local`，标题原文为 **AAMAS第一篇论文撰写保证被录用**。只读，不向该线程发送消息，不修改第一篇文件。标题是任务名称，不是本报告承诺。

## 比较对象与成熟度

第一篇：*Learning Joint Recovery of Multi-Agent Graph Optimization for Satellite–Ground Scheduling*。已完成归档是 `第一篇基础版本-v0.2.zip` / `v0.2-base-paper`；当前源码与线程正在进行 v3，已有训练/验证探索和新平衡设计，但 `paper/sections/results.tex` 等最终章节尚未集成。以下明确区分完成的 v0.2 和未完成的 v3，不能用旧版完整实验数量充当新机制确认。

第二篇：*LLM-Guided Synthesis of Constraint-Adaptive Heuristics for Satellite–Ground Scheduling*。v03 的形式实现、机制归档、development/discovery/scalability 已完成；本地 11:31 快照尚无 primary 840-context 与 transfer 216-context 完成归档。随后已补读最终 `frozen_joint_001.json` 和执行预算修订：主 guided 是 whole-pair utility 选中的 g05，minimum-interface g03 独立为 ablation；程序与候选保持冻结，bounded002 每 constructive programme 五 CPU 秒并显式保留 timeout。下述开发数值都是 development/validation，不是 test。后续实际归档可补充这一状态。

两篇共享 MWIS 和部分 C3 来源，但任务与统计量不同：第一篇从 incumbent 出发选择复合调整动作，以同核执行的接受增益为目标；第二篇构造完整可行 schedule，并离线提炼条件排序与特征接口。第一篇的“相对教师恢复保留率”和第二篇的“相对浮点 MILP 上界 schedule ratio”不可数值横比。来源规模、硬件与计时范围也不同，不能比较一个速度比就判断哪个方法更好。

## 同标准比较表

| 研究标准 | 第一篇 | 第二篇 | 公平判断与需要的证据 |
|---|---|---|---|
| 问题价值 | 多 owner 调整后，可兼容的恢复集与接受增益不能独立求和；预测应对齐实际执行核。 | 资源配置变化可逆转条件偏好；需要区分输入不足、规则错误和调度效果。 | 两者问题都成立。前者更直接对准动作执行，后者对准信息契约；只有自然发生率与强廉价控制才能说明实际价值。 |
| 近期文献差异 | learned move/delegation、coordination graph、DCOP 与结构化读出已有；容量约束是继承工具。 | heuristic evolution、joint features/policies、CEGAR、oracle synthesis 和 checker feedback 已有。 | 两篇都不能将“用图/LLM/反馈”本身当创新。第一篇差异应落在 execution-aligned joint recovery 与容量约束读出；第二篇落在 certified strict relations、exact quotient 和 full separation 的结合。 |
| 数学契约 | clique 容量归一化产生满足 clique inequalities 的分数 occupancy；执行核提供可行与 incumbent 不下降。 | 全残差 sound bounds；有限 scalar representability iff DAG；固定目录/feature limit 内全 separation 的加性最优。 | 第二篇的精确不可实现性与最优性命题较完整；第一篇约束读出是有用的结构约束，但不是可实现恢复值上界、整数可行集或全局最优证明。数量不同不意味着论文价值自动不同。 |
| 目标与部署对齐 | 标签是候选动作经过共同预算恢复核后的实际接受增益；选择与执行语义较近。弱教师仍是 procedure-dependent。 | 标签是明确 boundary 下最优 completion 的严格比较；当前下一动作经常选第三项，且部分边界从未达到。 | 第一篇的目标更贴近其执行；第二篇的证书更严格，但从 binary relation 到 greedy schedule 的桥梁更弱。两篇都要完整轨迹与实际成本，不能凭离线一致性作收益结论。 |
| 机制对照 | v3 同 encoder 自由读出、无 projection、edge projection、无 auxiliary、budget/owner 控制；强核与廉价 portfolio 压力。 | clique vs weight-sum、ranked vs uniform、具体 cycle 多轮 separation；guided/free/rule/enumeration 与 joint-selection controls。 | 第一篇需证明 clique 比 edge、容量比自由读出且实际贵核有空间；第二篇需说明自然 quotient 修复是否触发、引导是否胜过枚举。两者目前都有强对照压力。 |
| 独立冻结与统计单位 | 完成 v0.2 有图/来源边界聚合与多 seed；v0.2 跟进受首轮失败启发，已见源不构成独立确认。v3 新 balanced test 尚待完成。 | v03 拟冻结 programme/pairs；两个配置成对，跨 regime 共享 seed 聚簇，C3 原始 block 聚簇；最终归档待核。 | 不把训练 seed、动作、预算、重复计时或嵌套窗口充当独立来源。两篇都应以新冻结 test 确认，而不是让大量 records 淹没独立单位较少的事实。 |
| 强基线与负结果 | v0.2 部分 transfer 上 cheap sum 更强，small-case learned inference 更慢；v3 greedy portfolio 很强，mature solver 还能超过弱 teacher。 | deterministic enum 与 rule-only 的 validation quality 更高；natural quotient DAG；pair escape 多；编译比较是固定 validation rule。 | 两篇的失败都有科学信息，须进入主文。只对 Immediate、不可行总和或弱 scalar 比较会夸大贡献。 |
| 完整调度与真实资源 | v0.2 有 C3/W3 完整轨迹，但继承谓词、原 owner 为时间分区，未保存全部集合独立重建；v3 在重建真实 satellite owner 与资源。 | 保存 schedule/原始 ID 并规划源谓词独立复查；严格限于 frozen pairwise predicates、静态配置与 contact-duration objective。 | 两篇都不能把 C3 名字或大量 contacts 当独立物理可靠性。第二篇预期的 saved-selection source audit 更可复查，但审查快照尚未完成。 |
| 图表说明 | v3 有机制/coordination/solver exploration 图，已标 exploration；真实质量–时间 frontier 尚缺。 | 动机、流程、refined cycle 和 compile schematic 清晰；关键 frozen quantitative 图仍待填。 | 第一篇不能把探索 CI 标成确认；第二篇不能让多张示意图替代实际 incidence、强对照与 execution relevance。 |
| 成本与边界 | end-to-end 动作提议/响应/推理/执行；small-case overhead 与优化 lookahead 的真实基线必须保留。 | offline certificates/proposals/validation 与 online compile/deploy 要分开，含 amortization；dense update 可能昂贵。 | online 无 LLM 是部署事实，不自动意味着总成本更低。两篇必须报告实际时间而非仅抽象工作量。 |

## 第一篇：已完成证据与当前 v3 的区别

完成基础版有 24 checkpoints、11,776 主决策记录；两轮共 48 个完整策略/初态/版本轨迹，另有 48 个匹配的优化核重跑，不能称为 96 个独立单位。结构化同分布的 JointRecovery 接受增益高于原 Additive；v0.2 同分布均值 1.802 vs 1.662，同候选/同核 teacher 1.820。然而 v0.2 卫星局部 Joint 0.939，cheap all-replacement-sum 0.946，teacher 0.947；完整 W3 也没有超过廉价策略。该版本不能支持“卫星域普遍必要”或“优于成熟求解器”。

旧收益计算重复处理全 incumbent 放大前瞻开销。经局部差量等价复核后的全图在线节省约 19–25%，不应沿用原约三倍；小实例 CPU/GPU 均比 lookahead 慢。其完成稿诚实公开这些边界，是研究完整性上的优点。但 v0.2 物理/owner 语义与独立确认不足，需要当前 v3 重新补齐。

当前 v3 `RESULTS_ANALYSIS.md` 开头明确全部来自训练/验证探索、正式 test 未读取。探索中的 CliqueCapacity 对 FreeGNN 的 paired normalized regret 差为 -0.5678，CI [-0.8622,-0.3032]，说明约束读出的机制有候选价值；对 EdgeCapacity 的差 -0.0308，CI [-0.1403,0.0813]，对 GreedyPortfolio 的差 +0.0407，CI [-0.0122,0.1170]，不能认定 clique 超过 edge 或模型超过 cheap portfolio。

mature solver 在抽象菜单域相对弱教师还有约 7–8% recovery 增益，资源域未见此空间。强核验证中 cheap portfolio 接近 99.68% 同核保留，仅 9/81 菜单图出现正 selection regret，resource 为零。不能把已见这 9 图重新挑成 test。这些是检验方法价值的关键反证，比“教师保留 99%”更重要。最新线程在推进平衡设计与同核强对手，目前不据此宣称最终 v3 成功。

## 第二篇：形式强度与经验薄弱点

第二篇对 representation impossibility 的陈述比第一篇的分数 occupancy 更强，但也更窄：strict requirements、完整可见 exact features、有限 occurrence、无限制 pointwise scalar function。对目录中 feature 的最小修复是固定正加性 surrogate 加固定 feature limit 内的全局最优，不是 joint programme/shared work/完整 schedule 的最优。

重要区别是两篇都用 clique 但用途不同。第一篇的 clique inequalities 限制预测 occupancy；C5 等情况仍可分数过估，不能作为 certified recovery value。第二篇 partition/verified clique max 求和是数学 upper bound，结合可行 lower witness 和 exact arithmetic 支持严格关系。不能将这些放在同一“clique method”标签下互相转借保证。

第二篇当前自然时序/C3 商图无环，构造 probes 才触发不可能性；一次生成 batch 中 enum（约 99.44%）与 rule-only（约 99.42%）验证质量高于最终主 guided g05（约 99.32%）。旧 g03 的约 98.92% 是 minimum-interface ablation，不与新主程序混用。conditional evidence 的当前正文记录是 102 个 side requirements 中 escape 98 次，四次 pair decisions 与证书一致；这一 relevance 统计仍应核对是否属于最终 g05。它说明一致性尚非执行改善保证。当前 frozen test 完成前，不能把 development scale、compiler validation 或构造 probe 的修复成功当成 generalization。

五 CPU 秒 cap 是在无 cap pilot 暴露昂贵 no-cost programme 的执行问题后增加，报告声明未读取 test quality 调整候选，原始 partial 保留。公平分析需同时报告 completion/timeout、completed-case quality 和真实 CPU/wall；HiGHS 十秒与 local search 两秒是单独比较预算，不能称相同时间。透明预算修订比隐藏失败更可靠，但也不应把该 cap 写成从最初就已冻结的设计。

因此第二篇最有价值的证据不是多跑相似规模，而是：自然 contradiction incidence；完整 eligible joint selection 与 minimum-interface ablation 的分开冻结；programme provenance；强基线下 family-wise frozen quality–cost；boundary reachability/escape；C3 saved schedules 源谓词独立复查。这些能判断机制何时发挥作用，而不是仅证明代码跑得通。

## 与两份已发表参考论文的同标准关系

DRAGON 的原 PDF 展示 per-instance decomposition/reconstruction、边界约束、checker/experience 和四域/四模型/component ablation，同时报告 model API/token/运行成本。它已经具备 contextual feedback。第二篇的 offline frozen programme 和第一篇的 learned scorer 都不能仅凭“在线少用/不用 LLM”主张优越；需按部署次数说明 amortization 和质量。DRAGON 的 multiple-knapsack/bin-packing 等数值也不能直接对比这两篇 MWIS 调度。

VEXW 的 universal graph-motion solvability 是结构理论，使用 exact equivalences、条件算法与图增强界，没有 experimental section。可借鉴其量词清楚、具体 witness 图与限制条件的组织，不能把它当作经验 benchmark 规模或免评估范例。

第二篇文献审计已包含 EoH-S、2026-10-01 正式发表 LACE、CEGAR 和 joint symbolic policy/feature 先例。第一篇需要同样明确 capacity constraint、structured scoring、learning to delegate 与已有协同图学习的继承部分。两篇的创新都是针对各自执行/信息问题的机制结合，不是“首次用图”或“首次联合学习”。对 LACE 只核验官方摘要，应避免臆测其未读全文不存在某类能力。

## 最值得进入各自 8 页主文的证据

第一篇优先：执行对齐的 nonadditivity 小例；capacity projection 的准确保证及 C5 限制；相同 encoder/projection/edge/auxiliary 的机制差；strong cheap/strong teacher 的独立 frozen regret 与实际决策时间；自然 resource 域排序改进空间；完整调度新增收益而不是被巨大 initial objective 淹没的总 reward ratio；真实 owner/源谓词限制。完整模型、候选清单、原始日志、全部探索敏感性与 provenance 移到复现文档。

第二篇优先：sound boundary/evidence 契约；representation equivalence 与 full-separation 最优性的准确量词；具体 equality joins 与 surviving-cycle 例；自然零环与构造分层；四提案/枚举 arm、gate 与最终身份；强基线 frozen schedule quality–cost 与 pair escape；固定-rule 编译计时范围及验证属性。完整 prompts、源码哈希、endpoint/cut 明细、solver status 和 primitive 实现移到复现 MD。

两篇都要减少“流程看起来完整”的版面，优先让图解释一个真实证据链：机制在哪里激活，廉价替代是否已经足够，真实执行付出多少成本，结论在哪些域失败。图例必须区分 exploration/validation/test/transfer；单方法区间是否重叠不能替代配对差区间。

## 最终比较结论

第一篇完成基础版的执行实验更成熟，当前 v3 将强教师和真正资源语义作为核心压力测试；第二篇 v03 的形式诊断、sound evidence 和 exact finite repair 更清楚，但自然表示必要性、生成优势与执行收益仍需要区分。当前没有理由给两篇一个统一胜负、分数或录用概率。它们均有明确可研究的问题，也均受到强廉价基线、来源独立性和部署成本的实质约束。后续改善应针对各自缺失的因果桥梁，而不是追求相似的更多记录数。

## 本次主要证据入口

- 第一篇线程只读摘要；`第一篇/docs/FINAL_HANDOFF_ZH.md`、`docs/research_v3/RESULTS_ANALYSIS.md`、`BALANCED_DESIGN_FREEZE.json`，及当前 main/introduction/related_work/method/experiments。
- 第二篇当前 main/全部 sections；`docs/PUBLISHED_LITERATURE_V03.md`、`FROZEN_EVALUATION_PROTOCOL_V03.md`、`FORMAL_REVIEW_V03.md`；四个 `experiments/runs/v03/*.tar.gz` 完成归档。
- 用户提供的 `C:/Users/JIA/Downloads/SBAY6258.pdf`、`VEXW9837.pdf`，只作为已发表原文。

本报告没有改动或联系第一篇，没有将 development 结果说成 test，也没有保证录用或推测审稿分数。
