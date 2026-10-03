# V03 全稿独立冷审：研究完整性与可支持的创新

审查日期：2026-10-03，Asia/Shanghai。该报告以本地 11:31 的归档为快照，并补读随后收到的最终 joint-selection receipt 与预算修订；正文和服务器实验仍在推进，后续归档应另加补记，不能让本报告的“待完成”自动变成最终结论。

## 审查范围与判断

已读 `paper/main.tex` 和全部输入章节、`PUBLISHED_LITERATURE_V03.md`、冻结评估协议、四个已完成 v03 归档的完成记录及相关结果、独立形式审查报告，并读取用户提供的 SBAY6258 与 VEXW9837 原 PDF。参考论文只用于核验既有工作与论证组织，不作为本方法的实验数据。第一篇的比较见另一份报告，本报告不改主文。

当前方法已经超出“给 LLM 加一个提示词”的层面：全残差上下界支持可弃权的严格关系；完整输入的精确商图将表示不足与规则错误分开；具体相等连接支持必要切割；每次主问题解后重建完整商图，支持有限目录内的加性最优修复。实际回放、预算未知状态、完整调度评价和共享表达式执行也都有实现。这些是可审查的研究机制。

但强机制与强经验结论尚不等价。当前自然数据没有触发表征不可能性，单批提案不能归因于 LLM 引导，条件排序几乎没有直接成为候选程序的下一步动作。稿件最稳健的贡献是**有形式边界、保留负结果的调度信息诊断与修复框架**；现有证据不能支持“自然调度普遍需要该修复”“LLM 搜索优于枚举”“证书一致性带来更优完整调度”。冻结测试完成后仍应逐项判断，不能用总体质量接近数值上界反推这些机制结论。

## 最高三个阻塞点及具体修复

这里的“阻塞”指阻止较宽的研究主张成立，既不是录用预测，也不是断言现有窄主张不能发表。三项按对中心研究问题的影响排列。

### 1. 表示修复的经验必要性目前只在构造探针上成立

62 个训练配对中的 ranked/clique 证据共 51 条：构造诊断贡献 32 条（24 reversal、8 preservation），时序/C3 贡献 19 条（2 reversal、17 preservation）。所有 64 条 strict self-loop 要求来自构造诊断；自然时序/C3 合并后的商图有 60 类、30 弧，没有环或自环。因此自然偏好确实可以改变，但它们尚未证明当前完整输入丢失了满足这些偏好所需的信息。

这直接影响注册问题的核心因果链。连续奖励和多个数值特征很容易让有限样本中的向量全部不同；商图 DAG 只说明无限制标量函数可以在这些已观察点上满足关系，不意味着输入有可泛化的充分信息，也不意味着有限规则语言能实现该函数。反过来，规则拟合失败不能当成表示不足。人为舍入或删除真实可见输入后得到的环，则属于另一个已声明的输入契约，不能代替原接口的自然反例。

**当前版本可完成的修复：**主文保留上述自然零环事实和构造/自然分层；动机图与修复图明确标注构造见证；结果标题采用“构造不可能性验证与自然发生率”，避免把自然 reversal 的数量称为自然信息冲突。用实际记录报告每个域的 occurrence 数、exact alias 数、strict self-loop/long-cycle 数和 unknown 比例，解释 exact equality 检测器的覆盖边界。

**若要支持更宽主张：**在不查看测试结果的前提下，另行预注册一个来源独立、具有合理离散奖励或重复资源语义的自然接口研究；说明离散化为何是部署接口而不是事后制造别名，统一所有 scorer 可见输入，并在新证据上同时报告冲突发生率、修复与规则语言失败。不得从当前已经看过的难例选一个“测试”子集。若仍无自然环，保留这个负结果，将表示修复定位为防御性审计能力。

### 2. 提案实验支持“这几个程序”，不支持 LLM 引导带来搜索优势

guided、free、rule-only 各一个独立 assistant batch、24 提案；有 8/16/24 前缀，但三个前缀最终选中程序不变。前缀是同一批次的嵌套样本，不能替代独立生成重复，也不能绘成“多轮引导持续改善”的证据。没有 token 使用量，预交付检查不同，故只有请求数和候选数匹配，不能主张算力匹配。

最终 `frozen_joint_001.json` 中 deterministic enumeration 的验证质量约 99.44%，rule-only 约 99.42%，高于主 guided `g05_diminishing_pair_discount` 约 99.32%；guided 与枚举均具有约 97.2% 的 strict-requirement consistency，free 为约 94.4%。较好的表示一致性与较好的调度质量本来就是不同目标，这个结果必须用于限定机制结论。rule-only 不受 joint arms 的一致性/无环资格门约束，也是不同程序选择过程；其质量比较有效，但不能简单归因于是否提供 witness。

**当前版本可完成的修复：**正文用相同表格列出所有四个生成/枚举程序的质量、一致性、资格门、特征及成本，明确这是一次程序级比较；同时报告每批交付、可解析、有效、过 gate、最终入选的数量。主文保留枚举质量最好和 rule-only 的低一致性高质量事实。minimum additive interface 只放在 ablation，主程序必须从完整 eligible feature–rule pair 集合按冻结效用选择。

**已核实的版本衔接：**旧 `discovery_001/frozen_programs.json` 写 `guided_exact_selected_interface=True`，选中 g03（98.92% 质量、94.4% consistency）；新的 `experiments/discovery/v03/frozen_joint_001.json` 明确 `joint_feature_rule_utility=True`、`minimum_interface_is_ablation=True`，主 guided 改为 g05（99.32% 质量、97.2% consistency），保存新的 selection details/prefix curves、输入 assessment hash 和 unchanged candidate-bank hashes，声明在任何 test outcome 读取前冻结。因此原先 94.4%/97.2% 差异不是已证实错误，而是选择目标改变。旧 receipt 保留为 development；主文验证、实际 relevance、测试和图必须统一绑定到这个新的主程序，不能混用 g03 的曲线或执行轨迹。

**若要作生成层面的结论：**预注册多批独立引导/非引导请求，统一可用接口、验证过程、有效候选预算和失败收费；在独立新测试上以批次为单位比较选择后结果，记录真实模型调用与 token 成本。新模型、新 prompt 或新批次不能看到本次测试后继续沿用旧测试标签。当前没有这些证据时，只需收缩结论，不必为了主文篇幅虚造显著性。

### 3. 条件证书与实际调度之间的桥梁薄弱，最终冻结评估尚待归档

正文当前记录：102 个 acquired side requirements 中 guided 达到 88 个 saved boundary，但从这些边界启动时，98 个下一动作逃离被比较的二元集合；四次留在集合内的选择都与证书一致。102 是侧要求记录口径，不是 102 个独立调度问题。这个结果说明 pair consistency 通常没有直接决定下一步动作。第三动作可能更合理，escape 本身不是错误；它意味着不能把二元证书当成执行政策或完整调度提升保证。

截至审查快照，本地 `experiments/runs/v03/` 只有完成的 `development_scale_001`、`mechanisms_001`、`discovery_001`、`scalability_001`。冻结协议规定的 primary 840 contexts 与 transfer 216 contexts 尚无本地完成归档；源 ZIP 不是完成结果。正文仍有 held-out、paired CI、source-verifier 等结果槽。已有 150-context 编译比较是非诊断**验证**、固定规则、三次交错计时，不能改称最终 frozen programme 的 held-out 速度结果。4,096-contact 压力测试也不能自动作为新来源泛化。

随后读取 `EXECUTION_BUDGET_AMENDMENT_V03.md`：初始无 inference cap 的评估在约 14 分钟后只完成 160/840 contexts，昂贵 no-cost g18 揭露执行预算遗漏；原始 partial 保留，programme bytes、banks、validation selection 与 test allocation 不变，声明未读取 test quality 来调候选。新 bounded002 采用每个 constructive programme 五个 process-CPU 秒，timeout 没有返回 schedule、没有 fallback；HiGHS 为十秒 reference，local search 两秒，三者不是相同 inference budget。该修订是对已观察执行成本的透明方案修正，不应称其 cap 从最初即已预注册。主文须报告 amendment、completion/timeout 与质量，保留无 cap pilot 为成本诊断；仅以 completed cases 平均质量会偏向 timeout 方法，必须并列全任务完成率并说明 paired difference 的可用样本集合。

**当前版本可完成的修复：**完成并归档预注册 primary/transfer，保存执行前 source/programme/input hashes、状态、求解器 gap、失败和实际时间；逐个已保存 C3 schedule 按原始 ID 重建源谓词检查。统计配对保留两个配置，时序共享 seed 跨 regime 聚簇，C3 按原始 source block 聚簇，域分开报告。比较 guided/free/rule-only/enumeration、廉价结构基线、局部搜索和成熟求解器，并以配对差及区间表达质量/成本关系，不能只展示各自“接近 100%”。HiGHS 浮点上界参考与 exact-rational decision certificate 明确分列。

**机制桥梁必须保留：**主文用很小表格报告 boundary reached、pair escaped、pair selected、conditional loss；若可从既有冻结记录复算，则另报下一动作的条件损失与整条调度质量，不能给第三动作凭空赋证书标签。完整调度收益若成立，也只支持该冻结程序在该测试分布的表现，不能独自证明来自 equality-join repair。minimum-interface、无一致性门、penalty 和 natural-validation-only 控制须保持原先冻结方案，解释其选中的程序与主程序是否相同。

## 形式论证与近期文献差异

独立形式审查及小随机穷举对照没有发现高严重搜索正确性缺陷。Proposition 1 的量词是有限证据上的无限制确定性 pointwise scalar function；Proposition 2 的量词是固定证据、固定目录、固定正加性成本和声明的 feature limit。必要 cut 加全商图成功检查，给出与该域全局最优 master 相同的修复成本。预算截断只能输出可行修复或 unknown/非最优状态。该结果不延伸到共享 compiled DAG 成本、整体后悔、动态目录，或 bounded DSL 的实现性。相关更细 proof 与源码测试见 `FORMAL_REVIEW_V03.md`。

clique cover 的 Upper envelope 是真实的 sound bound，区别于有偏预测值：每个 verified clique 至多贡献一个 contact，interior/outside 交叉冲突放松只扩大可行域；可行下界与 exact arithmetic/outward export 保持严格比较。clique-cover 方法及 set-cover 工具本身是既有技术，创新应落在与 residual evidence、observable quotient、concrete joins 和 repeated separation 的组合契约上，而不是声称发明 clique bound 或 CEGAR。

已发表邻近工作限制了宽泛新颖性说法：FunSearch/EoH/ReEvo 已做可执行启发式搜索；EoH-S 与最新 LACE 已做互补组合和时间约束进化；CEGAR 已做反例精化；Bonet/Francès 已做特征与策略联合学习；DRAGON 已提供边界约束、checker feedback 与运行中的 LLM 协作。可辨识差异是**经过 sound conditional completion 证明的 strict relations、完整输入 exact quotient 的不可实现性诊断、具体 equality joins 和固定目录 full-separation 最优性**。现有实验证据没有建立在以上工作之上的数值优势。LACE 目前仅核验官方已发表摘要，不能推断其全文缺少所有表示精化或形式检查。

两份 AAMAS 2026 参考 PDF 的启示也需准确：DRAGON 是多域经验系统，图将 checker、成本和组件可用性连起来，并公开收益与成本取舍；其 MKP 是 **Multiple Knapsack Problem**，不是 multidimensional knapsack。VEXW 是纯结构理论，没有实验段；其小反例、等价与有条件算法结果可以参考，但不能作为本论文免做经验验证或“实验风格”的依据。

## 8 页正文需要留下什么

必须在正文出现的证据：

1. 配对配置、同一可行 boundary、sound interval 与 unknown 的契约；一个完整算清的构造 alias，避免读者将动机当作自然频率。
2. Proposition 1/2 的限定量词；具体 joins 和“廉价初始 cover 仍留下 refined cycle”的图，说明完整 separation 的必要性。
3. acquisition 对照及构造/自然分层，包括自然 zero-cycle。较多 reversal 与较多总证书的不同结论也应保留。
4. 最终 frozen hold-out/transfer 的 family-wise 配对质量/真实成本与强基线；主程序身份、gate、freeze 来源；枚举与 rule-only 的真实优势。
5. 一次小表或图中的 reachability/escape 和 compile trace equivalence/cost 边界；一段简短 scope/失败限制。

主文建议用两张紧凑定量图承载第 3–5 项：第一张将 certificate yield、node cost 和 natural/diagnostic incidence 放在并排面板；第二张画 frozen family-wise quality–cost 加关键配对差/CI，并附很小 execution-relevance 面板。图必须标 train/validation/test/transfer，不能把 development 曲线着色成 test。平坦 8/16/24 前缀直接小表即可，没必要占一张暗示搜索进步的大折线图。

若空间不足，优先将 problem-resource schematic 与 compiler implementation schematic 移至复现 MD，或合并成方法小面板；不要删掉自然零环、强对照胜出或 escape 数据来保留更多流程图。目前多个跨双栏概念图的版面投入很大，关键数量证据的优先级应更高。

适合放到 MD 的内容：完整 prompt/source receipts 和提案清单；逐表达式 DSL/类型规则；完整 cut endpoint 表与 exhaustive crosscheck 明细；source ID/predicate/hash 清单；全 benchmark/失败日志、solver status、每族 bootstrap 明细；编译原语和 stale-neighborhood 防重计细节；所有规模压力曲线、敏感性表和额外示意图。MD 能提供复查深度，但不能替代正文最关键的负结果和实验完成状态。是否可另附正式 supplementary material 要按实际投稿规则决定，不能假设审稿人必读本地 MD。

## 审查结束时的可操作顺序

新旧 programme/freeze 数值来源已经核实；接着核对实际 relevance 是否对应最终 g05，再纳入 bounded002 primary/transfer、timeout 和原始源谓词检查；据这些结果缩窄实际收益陈述；最后用两张定量图替换低必要性的概念图。若自然冲突与生成优势继续缺乏支持，保留完整形式机制，诚实报告其经验适用范围。不要临时寻找一个对方法有利的子集或增加结果导向的“确认实验”。

本报告没有给出录用概率或审稿分数，也没有将开发结果升级为测试证据。
