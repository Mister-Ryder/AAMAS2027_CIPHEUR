# CIP-Heur 0.4.0

**LLM-Guided Synthesis of Constraint-Adaptive Heuristics for Satellite–Ground Scheduling**

公开仓库：[Mister-Ryder/AAMAS2027_CIPHEUR](https://github.com/Mister-Ryder/AAMAS2027_CIPHEUR)。本项目用独立的离线认证界构造条件动作偏好，再检查完整特征输入是否能表达这些严格关系。具体商图循环与等值连接指导 typed 特征修复；冻结的特征—规则程序在固定可行构造内核中部署。

v0.4 增加同一条件残差中的共同连通分量消去、实际到达状态的有限动作池审计，以及按评分分支需要执行的特征计算。后续 score-local heap 是保持冻结 AST 的独立执行扩展。部署无需在线 LLM、条件值 oracle、API 密钥或原始卫星数据。

## 运行冻结程序

从仓库根目录运行。核心包只需 Python 3.10+ 标准库；输出路径自行选择，避免覆盖已有证据。

```text
python -m pip install -e "."
python -m cipheur --help
python -m cipheur schedule --graph examples/deployment_graph.json --program examples/frozen_program_v04.json --backend demanded --output output/demo_v04/demanded.json
python -m cipheur schedule --graph examples/deployment_graph.json --program examples/frozen_program_v04.json --backend heap --output output/demo_v04/heap.json
```

这两个示例命令已实际核验：均返回可行选择、reward 13，完整 trace 与选择相同。示例是小型部署检查，不是基准质量结果。可用后端为 `interpreted`、`compiled`、`demanded`、`heap`；后两者使用相同评分语义，heap 对未通过局部依赖检查的程序采用完整重评分。

冻结主程序见 [examples/frozen_program_v04.json](examples/frozen_program_v04.json)：

```text
nc = clique_cover_weight(neighbors(root))
score = weight / max(0.000001, weight, nc)
```

`nc` 是邻域的确定性加权 clique-cover 特征。这个比值是启发式分数，不是全局条件动作次序或调度最优性的证明。

## 已核验的研究证据

完整数值、失败分母、预算与独立核验见 [v04 结果报告](docs/RESULT_ANALYSIS_V04.md) 和 [v04 证据审计](docs/EVIDENCE_AUDIT_V04.md)。这里的质量百分比相对于保存的最强可行比较解，不能当作已知最优值百分比；精确 clique 上界和浮点 HiGHS 端点分别保存。

| 证据 | 实际范围与结论 |
| --- | --- |
| TRAIN 冻结选择 | 33 对、66 场景、93 程序；6,138 次分配中 5,996 完成、142 失败。新 guided 银行由一次实际离线助手会话产生 12 提案，与既有 24 提案控制银行并非数量或计算匹配。 |
| 表示与评分 | 主程序的完整接口商图无环，但仅符合 631/824 个保存的严格 TRAIN 次序；其中实际动作要求 596/788、既有要求 35/36。DAG gate 保证有限输入上存在某个不受限拟合分数，不能保证冻结规则逐条拟合。 |
| 单独消去控制 | 在相同未匹配分量界的 396 个 TRAIN 比较中，199 个区间严格变窄；严格证书数量仍为 33→33。不能宣称独立严格产出增加。 |
| 新鲜调度确认 | 主程序完成全部 456 个 test 场景；standard、dense/long、C3 的 competitive reward 分别为 99.46%、96.11%、97.56%。132 个新鲜 validation 场景不参与程序选择。公开 MWIS 实现通常获得更高 reward，其中若干也更快；没有 SOTA 优势结论。 |
| DIMACS / SATLIB | 固定 96 场景及单独预声明的 21 场景长预算子集已归档并由独立审计核验；保留逐方法/seed 失败、完成率与成本。单位权重和 hash 权重共享源拓扑，按族分别报告。 |
| SNAP 独立扩展 | 四个源图、八个场景，4,039–12,008 顶点；显式简单图投影保留顶点、去重并删除自链接。原五秒 full-scan 主程序完成 0/8；不能以失败后的执行扩展替换原确认结果。 |
| 五秒 heap 扩展 | 冻结 AST 在 456 新鲜场景的 2,736 个可比较后端对中 trace 完全相同。稀疏图 full scan 全部失败，heap 主程序完成 7/24 重复；此时没有稀疏配对速度或 trace 证据。dense degree 的运行开销反而增加。 |
| 固定程序实际动作审计 | 588 场景、3,526/3,528 个 rollout 完成；两个 free validation C3 rollout 失败。独立重放 1,071,174 个分数。主程序 555 个实际 sampled test 状态中，18 个 finite-pool regret 为正、191 个为零、346 个未知；不等于全动作或整个调度 regret。 |
| 单独三十秒 SNAP heap | 96 次分配全部有记录；主 heap 完成 12/24、degree heap 24/24，两个 full-scan AST 各为 0/24。仍无可比较 full/heap 对，不能报告稀疏配对速度或后端 parity；成功的同 AST 跨预算 trace 检查与此不同。 |

原 v03 的负面结果完整保留：[结果分析](docs/RESULT_ANALYSIS_V03.md)。自然 temporal/C3 证据尚未认证表示信息障碍；全部 200 扩展 alias 查询仍未知。修复最优性只覆盖固定证据、有限 catalogue、特征限额和可加独立特征成本，不能推广到共享 DAG 成本、整个启发式或所有实例。

上述固定 AST 动作与三十秒执行扩展分别通过 330,923 和 123,726 项独立审计检查。它们保留独立结果与预算版本，不改变程序、TRAIN 选择或原五秒实验。动作界的部分大分量上界依赖 hash 核验的 sound-oracle 执行收据，未保存完整 branch-and-bound frontier 证明；不能把全部严格标签说成独立完整证明的自然表示障碍。详见 [固定动作审计](docs/FROZEN_ACTION_AUDIT_V04.md)。

## 测试与证据回放

研究与绘图依赖使用可选 extra。主控已核验 181 项核心/研究测试通过（107.398 秒）；后续窄范围审计 CLI 另经只读归档回放，三十秒 runner 预算 guard 通过七项相关测试。下列命令可在安装环境中运行。

```text
python -m pip install -e ".[research]"
python -m unittest discover -s tests -q
python scripts/verify_artifacts.py
python scripts/verify_release_v04.py
python scripts/audit_selected_scores_v04.py
```

`verify_artifacts.py` 核验既有 v0.2 目录收据。`verify_release_v04.py` 核验发布文件 hash、归档清单与八项研究的完整分配记录，使用标准库；可选 `--paper-layout` 需要 pypdf，检查实际 PDF 的8页正文与1页参考文献。二者不能替代 v04 科学审计。TRAIN score audit 直接读取已发布的 TRAIN 归档，检查源 hash、全部 824 要求及 4,676 个参考/编译评分，并产生 JSON、Markdown 与独立机制图；它不会重跑调度、oracle 或选择。详见 [TRAIN 评分诊断](docs/SELECTED_SCORE_AGREEMENT_V04.md)。

v04 原始证据位于 `experiments/runs/v04/`，执行源版本位于 `experiments/source_snapshots/v04/`，独立审计与分析位于 `experiments/analysis/v04/`。`complete.json` 中的执行完成只表示请求均被记录；不表示全部方法成功、最优或物理可行。

五个归档审计入口已使用发布的归档/源 ZIP，并提供路径参数。下面命令将新报告放在独立输出目录，保留原报告的日期与检查范围。

```text
python scripts/verify_v04_training.py --output output/audit_v04_train/training.json
python scripts/verify_public_inputs_v04.py --output output/audit_v04_public_input/public.json
python scripts/verify_sparse_inputs_v04.py --output output/audit_v04_sparse_input/sparse.json
python scripts/verify_advanced_results_v04.py --archive experiments/runs/v04/advanced_public_v04_001.tar.gz --dataset public --output output/audit_v04_public/results.json
```

TRAIN 额外本机缓存只在指定 `--local-cache` 时比较；public input 默认核验已发布的 32-case native preflight，额外旧 smoke 只在指定 `--native-smoke` 时核验。可选检查改变新报告的计数，不改写旧报告或研究结果。

C3 物理重建需要 hash 匹配的 `DAI2026_SNSD_V51_STABLE` 原始包与 CSV；将下面占位路径替换为实际原始包目录。图级部署和公共图回放无需该包。

```text
python scripts/verify_fresh_inputs_v04.py --stable-root PATH_TO_FROZEN_V51_SOURCE --output output/audit_v04_fresh/inputs.json
python scripts/verify_advanced_results_v04.py --archive experiments/runs/v04/advanced_fresh_v04_001.tar.gz --dataset fresh --stable-root PATH_TO_FROZEN_V51_SOURCE --output output/audit_v04_fresh/results.json
```

输入、源模块与 CSV hash 先于物理重建核验。各脚本 `--help` 提供 `--archive`、`--source` 等覆盖参数；fresh input 还可指定 `--generator-source`、`--freeze-archive` 和 `--prior-root`。未发布的原生成 wrapper 明确记为 unavailable，实际生成模块仍按归档核验。部分历史报告和后续专项审计保留本机路径/缓存要求，不能把忽略的 `.research` 缓存当作 clean clone 已存在的文件。

## 重新准备公开输入与运行比较

下面两个命令下载既定公开源并保存转换/hash 收据；使用新的输出目录。

```text
python -m cipheur.public_benchmarks --config configs/public_benchmarks_v04.json --output output/public_inputs_v04
python -m cipheur.snap_benchmarks_v04 --config configs/public_sparse_v04.json --output output/sparse_inputs_v04 --archive output/sparse_inputs_v04.tar.gz
```

DIMACS clique 图使用独立集补图约定；SATLIB 使用 literal-conflict 归约；hash 权重是显式扩展。SNAP 的自链接投影改变原 looped-graph MWIS 语义，不能宣称保持那个原问题。见 [公开稀疏协议](docs/PUBLIC_SPARSE_EXTENSION_V04.md)。源获取与输入核验不等于算法效果。

实际 published baseline 比较需要独立编译的 CHILS、M²WIS、Struction、WeightedBR 官方程序以及 SciPy/HiGHS。将 `configs/advanced_*_v04_remote.json` 复制为本地配置，按实际编译产物设置 executable 路径/hash；保留版本、原图、F/X、seed、预算和预声明子集。远程绝对路径不是可移植安装目录。程序来源、输出映射、三 seed 均值、失败规则、五秒 soft/native、五 CPU 秒 cooperative、十秒 HiGHS、两秒 local 和单独三十秒子集见 [advanced 比较协议](docs/ADVANCED_COMPARISON_V04.md)。这些预算不表示总计算匹配。

```text
python -m cipheur.advanced_study_v04 --data SAVED_data.json --frozen TRAIN_frozen_programs.json --config LOCAL_advanced_config.json --output NEW_RUN_DIRECTORY --workers 4
```

TRAIN 重放与新鲜输入的具体命令见 [方法协议](docs/METHOD_EXTENSION_V04.md) 和 [冻结后确认协议](docs/FRESH_HOLDOUT_PROTOCOL_V04.md)。重新研究不能用已见 test/public 结果替换已冻结的选择；新设计应保留另一份协议和独立输入身份。

## 论文、图表与出处

交付入口：[最终论文 PDF](paper/main.pdf)、[本轮交付记录](docs/DELIVERY_V04.md)、[全部发布文件与证据的核验清单](manifest/RELEASE_V04_SHA256.json)。

- [paper/main.tex](paper/main.tex) 使用未修改的官方 AAMAS 2027 class、字号和边距。当前为八页正文、一页参考文献，含八幅主图和两张表，已逐页检查。官方类默认 conference 调用的条件闭合缺陷使用精确守卫修复；九页文字及 120-dpi 显示逐页相同，见 [模板兼容性核验](docs/TEMPLATE_COMPATIBILITY_V04.md)。最终导出/hash 由发布记录确认；工程状态不充作论文结论。
- [最终科学冷审](docs/FINAL_COLD_REVIEW_V04.md)、[正式发表文献核验](docs/PUBLISHED_LITERATURE_V03.md)、[autoresearch ledger](autoresearch/loop-261003-v03/results.tsv) 分别保存论证审查、文献来源和保留/否定决策。
- [实际助手参与](docs/AI_ASSISTANCE_V03.md) 与 [v04 提案会话收据](docs/V04_PROPOSAL_AUTHORING.json) 记录 root 核验的 `gpt-6.1-sol`/ultra、零 external API 调用和未知 token 用量。没有在线 LLM 或模型层面优势主张。
- 科学图为源数据驱动的 vector PDF；draw.io PDF/PNG 带可编辑 XML。图像重建还需要 Arial、Pillow、pypdf；示意图 builder 使用 Windows draw.io Desktop 与 PowerShell。已有发布 exports 可直接使用，Linux 安装 research extra 并不自动提供这些工具或字体。详见 [图表设计与审计](docs/FIGURE_DESIGN_V03.md)。

多文件论文在既有 TeX 环境中编译：进入 `paper/` 后依次运行 `pdflatex main.tex`、`bibtex main`、两次 `pdflatex main.tex`。不要用字体或边距修改规避正文页数。旧版基础说明保存在 [README v0.2 归档](docs/archives/README_V02.md)。
