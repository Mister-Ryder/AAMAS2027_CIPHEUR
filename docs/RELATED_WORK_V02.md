# 第二篇 V02：近邻文献与可检验的创新定位

本笔记依据用户最终采纳的摘要和引用对话《论文创新性强化 misava》。对话内容作为研究背景使用；当前执行范围以用户提供的最终摘要为准。研究对象是**不同资源约束配置下的一组静态调度问题**，不假定物理参数在单次求解过程中变化。离线干预用于获取监督，跨配置适应由同一个冻结程序接受检验。

以下方法定位是基于一手论文的比较判断，不是全领域新颖性证明，也不是实验优势结论。当前没有外部 LLM API 调用记录；助手根据训练证据提出候选属于 `prototype assisted offline synthesis`。回放这些候选可验证实现链路，不能充当自动 API 演化的效果证据。

## 1. 需要正面承认的近邻

### Property-Guided LLM Program Synthesis for Planning

- 作者：André Grahl Pereira、Augusto B. Corrêa、Jendrik Seipp。
- 年份与来源：2026；作者正式出版页列为 **NeurIPS 2026**。本文细读版本为 arXiv:2605.16142v2，2026-05-18；没有补造尚未核验的卷号、页码或会议 DOI。[作者出版与引用页](https://mrlab.ai/papers/pereira-et-al-neurips2026.html)，[原论文](https://arxiv.org/abs/2605.16142)，[全文 §3](https://arxiv.org/html/2605.16142v2#S3)。

该文让 LLM 生成 PDDL 规划启发式，用 direct property 检查器返回具体失败状态及其后继，构成反例驱动修复循环。§3.3 对验证设置预算；超时且未发现反例时按通过继续，§6 明确不保证未见任务上的性质。我们不能把“形式性质、反例反馈、冻结启发式部署”单独称为创新。[方法与局限](https://arxiv.org/html/2605.16142v2)

本项目的区别应落在**当前表示是否能表达已认证关系**：把不同配置和动作实例映射为特征等价类，发现严格关系在商图上的环或自环，并让这种结构矛盾触发表示扩展。检查候选是否违反关系，与检查**任意当前表示上的逐动作评分函数是否都无法满足关系**，是不同的问题。后者仍属于既有程序合成和抽象细化思想的应用，不能因此宣称通用 CEGIS 或表示细化由我们首创。

### HeurAgenix: Leveraging LLMs for Solving Complex Combinatorial Optimization Challenges

- 作者：Xianliang Yang、Ling Zhang、Haolong Qian、Lei Song、Jiang Bian。
- 版本：2025 年 arXiv:2506.15196v2，2025-06-24。所核验作者论文页与官方仓库未给出可确认的正式会议信息，本文按 **arXiv preprint，2025** 引用。[作者论文](https://arxiv.org/abs/2506.15196)，[官方代码](https://github.com/microsoft/HeurAgenix)。

HeurAgenix 通过解轨迹扰动和较优/较差解对照提炼演化策略，在求解过程中按状态选择启发式；选择器可使用 LLM 或微调轻量模型。§3.3 用 Monte Carlo rollout 数据训练，并针对噪声设计双奖励。因此“对照决策、结构缺陷诊断、状态适应、轻量部署”已有直接近邻。[原文 §3](https://arxiv.org/html/2506.15196v2#S3)

我们使用同一竞争动作对在两个合法约束配置下的全图条件完成界，只有分离区间才能产生严格标签；未决区间保留为未决。表示商图的矛盾决定是否扩展可观察输入。部署目标是执行固定特征—规则程序，不依赖在线 LLM 或 rollout。应保留 HeurAgenix 式对照反馈作为对照，而不能把它描述为没有上下文或只看标量质量。

### Evolution of Heuristics: Towards Efficient Automatic Algorithm Design Using Large Language Model (EoH)

- 作者：Fei Liu、Xialiang Tong、Mingxuan Yuan、Xi Lin、Fu Luo、Zhenkun Wang、Zhichao Lu、Qingfu Zhang。
- 出版：**ICML 2024**，PMLR 235，32201–32223。[正式论文集](https://proceedings.mlr.press/v235/liu24bs.html)，[作者版本](https://arxiv.org/abs/2401.02051)。

EoH 联合演化自然语言启发式思想与可执行代码，结合探索及修改提示，用任务评价筛选。思想与代码共同演化并不等于我们的表示与规则细化，但二者都扩大了程序设计空间。区别应由认证关系的可实现性诊断和有成本约束的结构特征扩展体现。[正式方法摘要](https://proceedings.mlr.press/v235/liu24bs.html)

PMLR 的导出记录把第二作者写成 `Xialiang, Tong`；作者 arXiv 与官方仓库为 Xialiang Tong。下面 BibTeX 采用 `Tong, Xialiang`，保留正式出版字段。[作者记录](https://arxiv.org/abs/2401.02051)

### ReEvo: Large Language Models as Hyper-Heuristics with Reflective Evolution

- 作者：Haoran Ye、Jiarui Wang、Zhiguang Cao、Federico Berto、Chuanbo Hua、Haeyeon Kim、Jinkyoo Park、Guojie Song。
- 出版：**NeurIPS 2024**，Advances in Neural Information Processing Systems 37；官方 DOI 10.52202/079017-1381。[正式论文集](https://proceedings.neurips.cc/paper_files/paper/2024/hash/4ced59d480e07d290b6f29fc8798f195-Abstract-Conference.html)。

ReEvo 使用相对表现的短期反思、累积长期反思、交叉与精英变异推进代码演化；函数接口以外允许开放代码表示。因此“解释失败、成对比较、修复规则、自动发现启发式”均不足以区分本项目。我们的结构见证来自已认证要求在**受限可观察表示**上的冲突，而不是将语言反思本身视作优化证明。[原文 §4](https://proceedings.neurips.cc/paper_files/paper/2024/file/4ced59d480e07d290b6f29fc8798f195-Paper-Conference.pdf)

### Mathematical discoveries from program search with large language models (FunSearch)

- 作者：Bernardino Romera-Paredes、Mohammadamin Barekatain、Alexander Novikov、Matej Balog、M. Pawan Kumar、Emilien Dupont、Francisco J. R. Ruiz、Jordan S. Ellenberg、Pengming Wang、Omar Fawzi、Pushmeet Kohli、Alhussein Fawzi。
- 出版：**Nature 625，468–475，2024**；在线发表 2023-12-14，期刊引用年份为 2024；DOI 10.1038/s41586-023-06924-6。[出版原文与引用信息](https://www.nature.com/articles/s41586-023-06924-6)。

FunSearch 将预训练 LLM、系统评价器和程序数据库结合，可在固定算法骨架内搜索关键优先级函数。离线搜索可部署代码、固定可行执行骨架以及外部评价器不是本项目独有。这里应将认证关系、表示冲突诊断与成本化特征扩展作为具体机制，完整调度质量仍是必要评价。[原文 FunSearch 方法](https://www.nature.com/articles/s41586-023-06924-6)

### 与用户提供的 DRAGON 的关系

DRAGON 的细读见 `docs/DRAGON_REVIEW.md`。论文是 AAMAS 2026，DOI 10.65109/SBAY6258；本文再次核验其作者 arXiv，避免将其称作 AAMAS 2025。[作者版本](https://arxiv.org/abs/2601.06502)

DRAGON 在待解实例上调用 LLM 进行分解和局部重建，传递静态结构与边界约束，并使用可行性检查和尝试记忆。本项目针对跨配置复用的优先级程序和训练表示修订。不能声称 DRAGON 不优化质量、不使用上下文或没有反馈。直接解法与离线合成的成本需分别报告，并按部署实例数量讨论摊销。

## 2. 最终摘要中“一核心、两支撑”的精确落点

**核心：认证关系冲突驱动表示—规则共同细化。** 设全部动作实例为 `x=(graph, residual state, action)`，当前可观察表示为 `φ(x)`。每条严格要求 `x+ ≻ x-` 在特征商图上加入 `φ(x+) -> φ(x-)`。若出现有向环或自环，任何仅基于 `φ(x)` 的确定性逐动作实值评分函数都无法满足全部严格要求。此时反复调整同一输入界面内的评分公式不足以解决冲突，需要改变表示、改变策略类，或审计证据/实例对齐。

该命题必须包含限定：特征等价是**完整可观察向量的精确相等**；接近值、四舍五入相同、聚类相同仅是诊断线索。没有环意味着有限样本可由某个抽象实值映射满足，**不意味着具体 DSL 中存在可实现规则**，也不意味着迁移成功。命题不适用于能够绕过输入界面读取完整图、动作 ID 或历史的任意政策。核验应使用严格评分关系，不能用固定 ID 打破平分来伪造关系满足。

**支撑一：干预与条件完成证据。** MWIS 是最大化，故比较使用 `L(preferred) > U(other) + ε`。四个动作—配置组合都必须可行，`L` 来源为全图可行完成见证，`U` 来源为有效松弛或完整搜索前沿上界。两配置偏好相反是 reversal，同向严格偏好是 preservation。边界承诺为固定选择和明确排除；证书只覆盖该承诺下的完整残余图。超时或区间重叠不能给出认证标签。认证的是当前两动作的条件最优完成值，不能把它转述为该动作在所有后续启发式轨迹上都更好。

**支撑二：结构见证指导有类型的特征组合。** 向 LLM 提供别名实例、关系环和图结构差异，允许从节点、节点集合、边集合、标量的有类型库组合特征。例如兼容候选总收益相同，但其诱导子图内部冲突不同，`induced_edges(compatible(v))` 的聚合可分离原表示忽略的结构。`sum_min_weight` 等统计是可观察特征，**不是自动成立的 MWIS 上下界**，尤其不能因边共享端点而双重扣减后宣称认证。

**优势必须由评价得到。** 候选按关系一致性、完整调度质量和特征计算代价共同选择。最终冻结程序在未用于合成与选择的实例、约束配置及其交叉上测试。数学矛盾检测能解释一类规则修复失败；它本身不证明计算成本更低、质量更高、领域新颖性更强或新配置上完全适应。

## 3. 对照设计中的关键区别

| 对照 | 公平保持的要素 | 要回答的问题 |
|---|---|---|
| 规则修复、固定基础表示 | 同 kernel、相同关系和候选预算 | 认证别名冲突是否确实挡住规则修复 |
| 联合特征—规则搜索，无冲突指导 | 同 typed library、可用训练实例与 LLM/候选预算 | 定向扩展是否优于自由扩大表示 |
| 标量质量搜索（EoH/FunSearch/ReEvo 风格） | 同完整调度评价、相同 kernel 和可观察信息 | 关系证据是否提供额外收益，而不是输入优势 |
| 普通对照/rollout 关系 | 同动作对、查询成本，保留未决和噪声记录 | sound bounds 是否值得求证代价 |
| 去除 preservation | 相同候选预算与干预池 | 稳定关系是否减少不必要变化或回归 |
| 去除特征成本 | 同 feature library 和关系集 | 成本项是否改变质量—时延折中 |

除明确标注的 prototype 演示外，真正 LLM 方法比较须保存模型版本、提示、实际调用、候选原始输出及选择轨迹。所有方法必须隔离测试实例和配置；训练 oracle 的证书和标签只能用于离线监督，不得作为部署特征。不要将助手事先编写的候选回放称作自动 LLM 搜索。

## 4. 可用 BibTeX 字段

以下条目给主文维护者复制使用；这份笔记不直接改动论文参考文献。Property-Guided 的 venue 按作者给出的引用记录；HeurAgenix 按已核验 preprint 引用。

```bibtex
@inproceedings{pereira2026property,
  author = {Pereira, Andr{\'e} Grahl and Corr{\^e}a, Augusto B. and Seipp, Jendrik},
  title = {Property-Guided {LLM} Program Synthesis for Planning},
  booktitle = {Proceedings of the Fortieth Annual Conference on Neural Information Processing Systems},
  year = {2026},
  eprint = {2605.16142},
  archivePrefix = {arXiv},
  url = {https://arxiv.org/abs/2605.16142}
}

@misc{yang2025heuragenix,
  author = {Yang, Xianliang and Zhang, Ling and Qian, Haolong and Song, Lei and Bian, Jiang},
  title = {{HeurAgenix}: Leveraging {LLMs} for Solving Complex Combinatorial Optimization Challenges},
  year = {2025},
  eprint = {2506.15196},
  archivePrefix = {arXiv},
  primaryClass = {cs.AI},
  doi = {10.48550/arXiv.2506.15196},
  url = {https://arxiv.org/abs/2506.15196}
}

@inproceedings{liu2024eoh,
  author = {Liu, Fei and Tong, Xialiang and Yuan, Mingxuan and Lin, Xi and Luo, Fu and Wang, Zhenkun and Lu, Zhichao and Zhang, Qingfu},
  title = {Evolution of Heuristics: Towards Efficient Automatic Algorithm Design Using Large Language Model},
  booktitle = {Proceedings of the 41st International Conference on Machine Learning},
  year = {2024},
  volume = {235},
  series = {Proceedings of Machine Learning Research},
  pages = {32201--32223},
  publisher = {PMLR},
  url = {https://proceedings.mlr.press/v235/liu24bs.html}
}

@inproceedings{ye2024reevo,
  author = {Ye, Haoran and Wang, Jiarui and Cao, Zhiguang and Berto, Federico and Hua, Chuanbo and Kim, Haeyeon and Park, Jinkyoo and Song, Guojie},
  title = {{ReEvo}: Large Language Models as Hyper-Heuristics with Reflective Evolution},
  booktitle = {Advances in Neural Information Processing Systems},
  volume = {37},
  year = {2024},
  doi = {10.52202/079017-1381},
  url = {https://proceedings.neurips.cc/paper_files/paper/2024/hash/4ced59d480e07d290b6f29fc8798f195-Abstract-Conference.html}
}

@article{romeraparedes2024funsearch,
  author = {Romera-Paredes, Bernardino and Barekatain, Mohammadamin and Novikov, Alexander and Balog, Matej and Kumar, M. Pawan and Dupont, Emilien and Ruiz, Francisco J. R. and Ellenberg, Jordan S. and Wang, Pengming and Fawzi, Omar and Kohli, Pushmeet and Fawzi, Alhussein},
  title = {Mathematical discoveries from program search with large language models},
  journal = {Nature},
  volume = {625},
  pages = {468--475},
  year = {2024},
  doi = {10.1038/s41586-023-06924-6},
  url = {https://www.nature.com/articles/s41586-023-06924-6}
}
```
