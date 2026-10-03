# Introduction independent author review v0.3

独立负责范围：`paper/sections/introduction.tex`。本轮仅写入该节和本审查记录；不修改主文、代码、其他章节或 bibliography。

## 核心论点与篇幅

引言的单一论点是：在可认证的严格排序关系因当前完整特征接口发生冲突时，具体 equality-join 见证应指导结构表示修复，随后再检验规则、完整调度质量与计算成本。

去除 LaTeX 控制命令、引用键与标签后，正文 **646 words**，包含恰好 **3 项贡献**。篇幅为八页正文预算保留实验空间。全文最终是否恰好八页需要主作者在所有章节和图整合后的 PDF 上确认；本片段不增加手动分页或改变模板。

三项贡献分别对应方法中的以下合同：

| 引言贡献 | 方法依据 | 保留的精确范围 |
|---|---|---|
| Decision-relevant certified specifications | `sec:method:model`、`sec:method:certificates` | 实际 rollout 的 next-action anchor、相同 boundary replay、完整残余空间的 sound clique envelopes；严格区间分离才产生 reversal/preservation，未决为 unknown。 |
| Witness-guided representation repair | `sec:method:repair` | 精确完整向量的 quotient acyclicity 刻画有限已观测要求上的 unrestricted deterministic pointwise representability；只有 globally solved masters 且 full-quotient separation 以 DAG 终止时，才对固定证据、有限 catalogue、additive surrogate 声称最小成本。 |
| Executable joint refinement | `sec:method:features`、`sec:method:selection` | 类型化 feature–rule pairs、shared DAG、incremental residual aggregates、完整调度质量与实际 compiled work 进入选择。未声称非加性 DAG 成本继承 set-cover approximation。 |

## 动机图见证核对

引言引用主作者整合的 `fig:motivation`。示例是实现中 `diagnostic_pair("train", 0, "reversal")` 的单位权重尺度版本，边界已承诺的奖励从条件值中扣除。

- 两个 core contacts 的单位奖励均为 8，分别与三个单位奖励为 6 的 peripheral alternatives 冲突，并彼此冲突。
- 左侧 X triple 为 independent，Y triple 有一条内部边；右侧 X 变为 clique，Y 不变。
- 实际实现改变的是 **ground-station switching interval / `station_gap`**；`satellite_gap=0` 在两侧保持不变。已经向主作者指出不能将图标成 satellite-gap intervention。
- 直接调用既有 `features` 和精确 oracle，核实两侧状态中 a/b 的完整基础向量分别严格相等。
- 扣除 boundary reward 并除以生成器 scale 后，四个 conditional increments 依序为 **20、26、20、14**，偏好 **b → a**。这些是构造见证的条件完成值，属于数学动机说明，不是完整策略 rollout 的性能结果。
- 配置字段在同一状态中由 a/b 共享；引言没有声称两种配置之间所有特征向量相同。

图需要保留 conditional-value 标签，并清楚显示 X 的内部边变化。完整策略可能先选 peripheral contacts，绕过原比较；本文没有从该见证推断不可避免的全局调度损失。

## 论断与文献检查

复用 `references_v03.bib` 与 `PUBLISHED_LITERATURE_V03.md` 已核实的 9 个键：`augenstein2016optimal`、`levinson2025optimal`、`tao2023transmitting`、`romeraparedes2024funsearch`、`liu2024eoh`、`ye2024reevo`、`chen2026dragon`、`clarke2000cegar`、`frances2021policies`。所有引言引用键均在新 bibliography 中存在。本节未新增待核实引用，也未使用被排除的 preprint keys。

问题范围限定为可用 pairwise conflicts 表示的 hard constraints，不把 MWIS 联系人选择等同于完整 integrated mission planning。已有算法发现、checker feedback、abstraction refinement 和 learned planning features 被承认为先例，创新主张落在认证关系与 concrete equality-join repair 的具体合同上。

引言未写入服务器实验状态、交付过程、零 API 调用叙述或尚未执行的 measured superiority。结尾明确区分 observed relation representability、bounded-language realizability、complete-schedule quality 和 generalization；shared feature execution 也不提供后两者的保证。matched-budget 条件仅描述评估设计，没有预写结果。

## 静态检查与整合依赖

已检查：词数范围、3 个 contribution items、引用键存在、LaTeX 花括号/数学分隔与 enumerate 环境配对。见证数据通过上述实现接口独立核对，未改代码或生成任何实验记录。

这是输入片段，不是 standalone LaTeX 文档。本节不单独编译；主作者需将主文旧 introduction 替换为此片段，加入 `fig:motivation`，使用新 bibliography，并在整合编译后确认引用、图位置、列宽与八页正文限制。

采用写作技能：`C:/Users/JIA/.codex/skills/research-paper-writing/SKILL.md`，并读取其 `references/phase5-paper-drafting.md` 与 `references/writing-guide.md`。用户要求覆盖技能中的默认 Git 提交工作流，本作者没有提交或推送。
