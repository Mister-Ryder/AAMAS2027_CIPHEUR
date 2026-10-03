# 第二篇 v0.4 交付记录

日期：2026-10-03。公开项目：[Mister-Ryder/AAMAS2027_CIPHEUR](https://github.com/Mister-Ryder/AAMAS2027_CIPHEUR)。

## 论文与可编辑材料

- 主论文：[`paper/main.pdf`](../paper/main.pdf)，官方 AAMAS class 下 **8 页正文 + 1 页参考文献**，8 幅正文图、2 张表、24 条实际引用的正式发表文献。没有 arXiv 条目，没有改字号、正文宽度或页边距。
- LaTeX：[`paper/main.tex`](../paper/main.tex)，各节独立文件，各节由独立 agent 撰写后由主控审稿、缩减重复、校正结论与汇总。扩展稿保留在 `docs/archives/`，没有用实验日志填充论文。
- 五张机制示意图同时提供原生 `.drawio`、矢量 PDF 与 PNG。图4展示共同分量消去的数学作用；图5展示实际助手提案、typed AST 与评分/动作检查。图2明确分开离线助手、认证工具、冻结程序及在线可行内核。
- 完整统计、失败记录、预算、研究审查、AI 参与收据和工程说明分别在 `docs/`、`experiments/analysis/` 和 `autoresearch/`。这些材料是额外报告，不作为正文页数或论文结论。

## 方法与实验已经完成的范围

表示商图冲突、完整商图重新检查、有限 catalogue 的有条件最小成本修复、同一条件残差的共同分量消去、实际到达状态的有限动作池审计，以及冻结 AST 的按需计算和局部 heap 执行均有代码及范围明确的验证。有限输入商图无环与冻结分数满足全部关系是不同命题；摘要已精确使用“declared-interface acyclicity”，原采纳摘要保留在 `paper/ABSTRACT_TARGET.md`。

TRAIN 共 93 程序、66 场景；新鲜数据包括 132 validation 和 456 test 场景。公共算法数据覆盖 96 个 DIMACS/SATLIB 场景和八个 SNAP 场景，另有预声明的长预算子集。实际比较包含官方 CHILS/ILS、M²WIS、Struction、WeightedBR、HiGHS，以及经典贪心/局部搜索与合成控制。主控完成 181 项测试，另有源 hash、原图可行性、数值、冻结身份、失败分母、成对 trace 和统计的独立审计。所有已经分配的服务器实验均已完成并下载；运行快照与原始结果均发布，不以部分完成的结果代替完整分母。

冻结主程序在 456 新鲜调度场景全部完成；standard、dense/long、C3 的 best-observed competitive reward 分别为 99.46%、96.11%、97.56%。它相对部分经典控制有收益，但未胜过已发表原生 MWIS 方法，公共稀疏图也暴露完成率限制。单独 heap 扩展在 2,736 个可比较的新鲜后端对上保持完整 trace 相同，standard 场景的平均配对 CPU 比约为 15.45；这不是相对先进求解器的速度优势。三十秒 SNAP 后续执行扩展仍保留原五秒结果和不可比较的 full-scan 失败。

LLM 的实际参与是一次持续的离线 `gpt-6.1-sol` 助手提案会话，新银行包含 12 个最终提案；不是 12 个独立模型调用。没有外部 provider API 调用或在线 LLM/oracle，token 用量未知。控制银行规模和计算不匹配，因此没有模型层面优势结论。见 [`AI_ASSISTANCE_V03.md`](AI_ASSISTANCE_V03.md) 与 [`V04_PROPOSAL_AUTHORING.json`](V04_PROPOSAL_AUTHORING.json)。

## 复现、审稿与交付核验

部署核心仅需要 Python 3.10+ 标准库；README 的 demanded/heap 示例均实测返回可行 reward 13。归档回放与重新运行研究分开说明：原生比较需要官方编译产物，C3 物理重建需要 hash 匹配的 V51 数据，图形重建需要对应绘图工具。额外报告不把这些条件包装成无依赖的一键运行。

最终所有九页已渲染并逐页检查。正文没有未定义引用或越界警告；参考文献在独立的一页中排版。应用内置编译器报告无法定位本平台目录，因此保留打开的源文件，使用本机既有 TeX 环境完成编译和 PDF 核验；没有安装或修改 LaTeX class。官方 class 默认 conference 参数缺失的兼容处理在最终冷审报告中说明，官方文件本身未改。

最终编译后另外渲染九页；第1、2、3、5、6、7、8页与已逐页检查的图像完全一致，第4页的段间距调整和第9页的平衡参考文献另行重新查看。两个独立审查员确认发布核验脚本的跨平台语法和完整分配/失败范围；实际 GitHub 版本矩阵结果单独观察，未用代码审查代替 CI 成功。

[`FINAL_COLD_REVIEW_V04.md`](FINAL_COLD_REVIEW_V04.md) 保留科学审查与证据边界；[`RESULT_ANALYSIS_V04.md`](RESULT_ANALYSIS_V04.md) 保存完整数值；[`FIGURE_DESIGN_V03.md`](FIGURE_DESIGN_V03.md) 保存统一样式、重点标注及图语义核验。`manifest/RELEASE_V04_SHA256.json` 和 `scripts/verify_release_v04.py` 核验发布文件身份及完整执行记录，不能替代各科学审计。论文录用由评审决定，当前证据不支持承诺录用或 SOTA 优势。
