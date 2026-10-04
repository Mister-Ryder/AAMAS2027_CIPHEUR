# 第二篇论文：专家审阅版本

这是2026年10月4日停止研究后的版本快照，仅用于专家审阅；没有重新运行实验或重构算法。

优先阅读：

- [当前论文 PDF](paper/CIPHEUR_AAMAS2027_V06.pdf)与[LaTeX源文件](paper/main.tex)。
- [完整研究结果与局限报告](docs/V06_FINAL_RESEARCH_REPORT.md)。
- [先进方法完整对比结果](experiments/analysis/v06/performance_tables_v06_002/PERFORMANCE_RESULTS_V06.md)。
- [训练收益链诊断](docs/V07_TRAIN_CONTRIBUTION_CHAIN_DIAGNOSIS.md)与[数据筛选数学判据](docs/V07_DATA_SELECTION_MATHEMATICAL_CRITERIA.md)。
- [大规模卫星场景分析](docs/V07_CONTACT_SCENE_SCREEN_002.md)、[表示碰撞数学分类](docs/V07_SCENE_ALIAS_MATHEMATICAL_CLASSIFICATION_003.md)与[公开数据适配审查](docs/V07_PUBLIC_BENCHMARK_SCENARIO_AUDIT.md)。

代码位于 `cipheur/`、`scripts/`，配置和示例分别在 `configs/`、`examples/`。结果表、分析和已保存的协议位于 `experiments/analysis/`、`experiments/discovery/`；当前正文分节源文件位于 `paper/drafts/v06/`。

审阅时请区分：信息门改善已经观察到；训练完整调度收益未拉开，预期最终调度优势尚未建立。报告同时保留有利、无增益和失败发现。新场景的严格决策证书尚未执行，不能把非对称结构当作严格偏好。

本次优先上传审阅材料。大体积原始运行归档、完整逐步日志、历史二进制分片及私有原始数据保留在本地，未纳入此快照；因此此包不是完整实验重放分发包。部分历史报告中的全量归档链接尚不可用。未上传密钥或服务器连接凭据。

`REVIEW_SHA256.json`记录已上传文件的校验值。
