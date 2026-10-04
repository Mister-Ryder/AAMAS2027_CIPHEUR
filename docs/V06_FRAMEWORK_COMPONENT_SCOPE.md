# V06：吸纳成熟优化组件，保持核心创新

本文件落实用户最新的方案调整，属于工程与实验解释；原始实验冻结、原始算法源码与所有失败记录不因此改变。科学论文只保留必要的接口、正确性和归因说明。

## 框架与优化组件的职责

框架创新是：用固定边界下的完整条件完成值认证严格关系；在实际特征向量的完整商图中发现 self-loop/有向环；由具体严格弧与相等连接指导离线 LLM 构造有区别作用的特征与排序规则；联合检查信息可表达性、实际规则拟合、完整解质量和计算成本。成本最小化结论仅适用于已冻结有限 catalogue 的独立正加性成本，不自动推广到实际共享计算。

可运行部署使用成熟 MWIS 优化方法提供的可行 incumbent，并在统一的可行性与局部搜索内核中执行冻结规则。V003 已在运行的两个分支分别使用 Degree 初始化与原生 CHILS(seed1, T/2) 初始化；warm 分支随后使用同一有界 repair(T/2)。每个 standalone warm policy 均承担完整的实际 CHILS 准备、调用、检查、child CPU 和自身 repair 成本。实际批次为效率共享一次初始化，但没有把共享开销从单独部署成本中删去。

CHILS 是真实使用的成熟原生优化组件。clique 上界、精确加权局部 branch-and-bound、保留旧解和仅提交正增益，是共同内核的经典优化原语。M²WIS、Struction、WeightedBR 则按其正式论文运行独立原生比较算法；当前实现没有把它们完整的 reduction、evolution 或 struction 系统冒充成自己的新方法。对应来源为 CHILS/ILS（SEA 2025）、M²WIS（Journal of Graph Algorithms and Applications 2024）、Struction（ALENEX 2021）和 WeightedBR（ALENEX 2019）。论文的方法只简洁说明这些公共组件的作用，在实验表方法名后给出正式引用。

## 必须分别回答的实验问题

1. **信息修复**：原始所有 proposal position 中，有多少获得 acyclic demanded interface；实际严格排序仍须单独检查。
2. **适应行为**：在同一对竞争动作、固定边界和成对约束变化上，排序是否共同满足严格 reversal/preservation；tie、未知区间和采样不足分别保留。
3. **调度质量与成本**：在相同内核和同一初始化条件下，成熟组件与所合成优先级分别带来多少真实可行收益、工作、CPU/wall、失败或未返回。
4. **可移植性**：五次已冻结 ID 双射的均值和最坏值，公开源数据的原始精确目标和 solver 数值支持范围。

生成阶段的 W/R/O 条件使用同一 typed library、相同请求设置和相同 proposal slots；实际 token 与时间并不相等。W joint 与 R/O quality-only 的直接比较含有选择器差异，不能声称它单独隔离了 witness 作用；对应 quality-only W/R/O 比较才共享同一质量选择规则，且仍条件于同一 R1 seed 和四个描述性 authoring blocks。

## 已支持的结果与待完成的结果

R2 TRAIN 的 matched 四个 blocks 中，W 的信息 gate 为26/32，R 为19/32；包括第五 block 后为28/40与24/40。该第五 block 倾向 R，始终保留。W 的实际 raw strict fit、joint strict fit 和选中 work 均没有全面超过 R。所有已评估 R2 TRAIN 候选的完整调度宏质量相同，不能将信息 gate 收益改写成已实现的调度收益。EoH-DSL 的四个质量选择全部保留 shared R1 seed，此结果也保留。

V003 的全部302contexts、3targets、23policy identities、cold/warm 两轨和全部 native requests，共52,548个原始位置已预声明并在云端执行。完整批次未终结、数学/收据核验未通过之前，不填写它们的性能结论。后续 R2/EoH heldout 与 TRAIN restricted-patch bridge 已按原始配置顺序排队，避免 measured workloads 重叠。

最终论文将以真实数据支持的优势组织主要结果，同时保留适当的负对照和性能限制。搜索组件的强表现不会被当作 LLM 独有贡献，信息 gate 的强表现不会被当作实际排序或排程收益。工程故障、hash compatibility、执行队列和完整审计记录保存在 MD/JSON，不用它们填充8页正文。
