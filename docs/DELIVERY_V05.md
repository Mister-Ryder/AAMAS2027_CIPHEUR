# 第二篇 V05 交付范围

日期：2026-10-03。公开仓库：[Mister-Ryder/AAMAS2027_CIPHEUR](https://github.com/Mister-Ryder/AAMAS2027_CIPHEUR)。本文档记录保留的V05候选与证据，不是本轮研究完成或最终发布声明。用户要求进一步重构算法、获得真实优势；V06结构驱动局部修复开发开始。V05服务器补测/平台核验仍待完成，安全发行准备暂停。

候选快照：2026-10-03 14:11:45 UTC（北京时间22:11:45）。`paper/main.pdf` 共9页，末页References；bibliography含36项。PDF SHA256：`a17b566e0616db7ba56b045aec26ce31527f12dbba32744ca4281f2640820fbc`，3,476,949 bytes。这是有日期的候选身份，不是未来修改后的最终公共hash；最后清单/CI与发布由root在研究完成后处理。

## 论文与图表

[paper/main.pdf](../paper/main.pdf) 当前候选为8页正文+1页参考、36条引用、6幅主图及5张表；最终视觉检查由 [FINAL_REVIEW_V05.md](FINAL_REVIEW_V05.md) 的独立负责人记录。不改官方字号、页边距或栏宽；表格单元格使用模板自带小字号。本次同步仅核对页数/引用数量，不替代逐页视觉审阅。

前三幅图集中表达：资源干预与信息别名；共同分量消去、LLM特征—规则合成与可行冻结内核；原生可编辑算法控制流。生成图采用二维数学/工程线图，去除卡通、立体模型和大段图内解释。节点、边、等价类、颜色与公式承担表达；文字说明放在图注。第四、五幅图展示实际约束敏感性、调度累积轨迹和原始提案槽位的TRAIN曲线，保留负面与交叉结果。

主baseline表保留十二方法×七总体的失败零质量与覆盖、正式引用；完整elapsed面板移入 [BASELINE_COMPARISON_V05.md](BASELINE_COMPARISON_V05.md)，正文保留Struction/primary实际成本与不同预算。其余四表保留LLM四区组、两个公共冲突、三行纯cancellation分层和冻结赢家transfer。六个独立矢量结果面板组成三组：约束增益/实际前缀、原槽位yield/TRAIN utility、同AST heap成本/探索性transfer完成率。原生字号与最终印刷尺寸分别核验，不将旧五面板布局的印刷测量套用到新候选。

## 完成的新增实验

- 三证据条件、四生成区组、每个十二原始槽位：144候选，66 TRAIN场景，9,504分配记录。所有输出先冻结，随后统一评估与选择。
- 统一冻结十二个赢家后生成108新问题对、216 TEST场景；十二赢家加共同Degree，共2,808/2,808完成。标签相对目标反馈平均质量差+0.657百分点；显式见证相对标签仅+0.014百分点。分别报告四区组和standard/dense分层，不将图级重复当作模型级重复。
- 公开信息诊断：13个完整单位权重DIMACS图、48个预定诱导子图状态；324实际查询与164无适合边的配额短缺保留。独立认证67个严格比较；完整图分别为2严格、28精确相等、74未知，诱导轨道为65严格、155精确相等。两个完整图案例表明现有主程序尚未修复全部障碍。
- 本机探索性transfer：十二原TRAIN赢家+Degree、已见96公开和24 C3场景，全部1,560分配有记录；1,007完成、553 cooperative CPU失败。Witness/Relations/Objective/Degree完成299/480、304/480、306/480、98/120；Witness C3完成91/96，另两arm各96/96。旧clique上界U和可行见证L保持分离，没有普遍Witness迁移优势；不是服务器确认或新独立holdout。见 [报告](../experiments/analysis/v05/matched_transfer_exploratory_v05_001_report.md) 和 [独立核验](MATCHED_TRANSFER_AUDIT_V05.md)。
- 纯cancellation分层：Standard216比较中197缩窄、median100.5→23、strict0→0；Dense108中0缩窄、43.875→43.875、strict17→17；C3 72中2缩窄、17060→17060、strict16→16。Exact Fraction逐行与总体396/199/33/61/302收据一致；不同权重单位不能跨族排序宽度难度。见 [深入实验审阅](EXPERIMENT_EXPANSION_REVIEW_V05.md)。

新增结果归档和实际执行源快照均位于 `experiments/runs/v05/` 与 `experiments/source_snapshots/v05/`。它们不覆盖V04冻结程序或任何旧原始证据；十个匹配实验语义模块保持执行时的字节身份。当前0.5版本仅更新发布元数据。V04整版可在固定提交 `de0f70565eb56ceb6c2d2324481017a94782ec62` 恢复。

## 核验与结论范围

本机transfer独立审计141,652检查零错误，覆盖完整trace、精确reward、固定U/L、120输入与十二赢家身份、130个初始argmax；不声称重算所有后续评分。runner收据另有105,253验证检查，范围不同。五秒meter在AST parse后建立；返回CPU/wall仍包含parse、初始化、调度、验证及晚超时，graph/source materialization单独记录。追加budget clarification未改变原protocol/source/预算/结果。

**待完成：**按用户要求服务器重放新增1,560分配，核查原2,808测试的平台并按结果追加同冻结程序服务器补测。本机与服务器分别保留source/config/archive和失败分母。服务器输出、新独立审计、最终public SHA/CI尚未到位，不能预写完成。最新V06重构要求也尚未实现，本轮不继续最终安全发行delta或发布准备。

最终matched独立审计391,317检查零错误；公开诊断独立审计7,441检查零错误；作者收据审计173检查零错误。结果分析另检查912,666项trace/可行性/均值/上界。这些检查范围不同，不相加包装为独立实验量。完整测试、页面与当前发布身份由最终复核记录；[复现入口](REPLAY_V05.md) 区分档案回放与重新执行。

公开baseline没有证明SOTA领先。新pilot只支持小规模描述性的标签引导收益，显式见证额外收益极小；没有LLM对非LLM的因果比较。完整接口DAG无环与冻结评分拟合全部824关系不同。公共算法信息障碍与物理卫星调度发生率不同。录用不能作为实验结果或交付承诺写进论文。

完整统计、失败、作者transport、模型元数据、成本、图生成迭代与工程事项分别放在 [MATCHED_LLM_RESULTS_V05.md](MATCHED_LLM_RESULTS_V05.md)、[AI_ASSISTANCE_V05.md](AI_ASSISTANCE_V05.md)、[GENERATED_FIGURE_SEMANTIC_REVIEW_V05.md](GENERATED_FIGURE_SEMANTIC_REVIEW_V05.md) 和其他MD报告，未把交付日志加入论文正文。
