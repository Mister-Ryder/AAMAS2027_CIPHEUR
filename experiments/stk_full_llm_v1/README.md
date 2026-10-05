# STK 全图 LLM 参数适应实验：专家复现入口

本目录验证离线合成的评分程序在**完整72小时卫星—地面站调度**中的作用。每次部署只接收当前图和冻结程序，在线 LLM 调用、条件完成值 oracle 调用均为零。先前 P0 的局部证书证明属于训练证据，不能替代本轮完整调度性能比较。

这份 README 是代码交付、执行与复现说明，其他 Markdown/JSON/TSV 是实验报告和迭代记录，均不属于论文正文。最终性能表、配置变化分析及不利结果由正式结果报告补充；此处不预写优势结论。

## 当前执行状态

- 已完成12次真实 CLI 调用，生成并验证96个LLM候选：三个条件×两组合成批次/重复请求×两轮×八名额。另有32个确定性 typed-grammar 候选、1个预先指定的旧冻结程序和7个传统比较方法。没有第三轮生成。
- 首轮 TRAIN 1408次、反馈轮 TRAIN 768次均已完成，四个机会库×四个 A/W/E/J 配置，2 CPU秒、seed 2。96个LLM与32个grammar候选各有全部16张图的完整调度与743条严格关系拟合记录；旧冻结和传统方法是独立控制。权威记录位于 `cloud/train_round1/`、`cloud/train_round2/`，须保留并区分程序内部异常、合法保底解和排序是否实际参与。
- `registrations/train_round1/` 的1296次本地预案**没有执行**，已写入 `NOT_EXECUTED.json`，不得与正式1408次合并计数。
- TRAIN预定三目标规则给每个LLM条件/批次及grammar池保留四个不同内容候选，共28个短名单程序。VALIDATION已完成560次：28程序+7传统方法，8图×2/10秒、seed 2。选出六个LLM程序（每条件/批次一个）及一个grammar程序，加预指定旧程序组成最终八程序。
- 最终程序和协议已冻结；1440次最终TRAIN已完成并下载 `cloud/final_train/`，1440/1440可行、0进程失败。原2880次主TEST因用户要求更改为当前实例自适应算法而取消；服务器保留1561个已产生的结果文件，属于未完成批次，不能当成完整TEST。两条旧队列的21个所属进程均已停止，未触碰其他项目。此轮TEST收益没有用于新算法设计；停止凭据见 `cloud/user_design_redirect.json` 和两份 `.cancelled.json`。
- 最终七个新选定LLM/grammar程序**全部 `features=[]`**，TRAIN完整base9的表示矛盾仍存在。最终调度比较可以评价冻结规则及其成本，不能证明新增表示修复成功；第八个旧冻结头的既有结构特征不是本轮新LLM贡献。独立诊断在 `analysis/selected_information_gate/`。
- [完整TRAIN结果与链条诊断](reports/完整TRAIN结果与链条诊断.md)列出全部15方法×2预算、真实费用与负提案；八个冻结头在TRAIN内均低于CHILS p4，两Witness头在两个预算均低于Degree。这是训练内部结果，不能以TEST分布变化解释。

## 主实验之外的固定辅助机制诊断

辅助v2已在读取TEST前独立冻结：`banks/frozen_feature_diagnostic8_v2.json`、`selection/feature_diagnostic8_v2_ids.json`、`protocol.feature_diagnostic8_v2.frozen.json`。八个程序为5个真实LLM特征候选+3个grammar特征对照，从既有固定短名单/参照规则取得，不按VAL或TEST胜负挑选，不替换主实验八程序。

其同预算seed 2计划为256次TRAIN、512次TEST，因方法方向更改已取消，辅助求解未启动。旧五程序方案也未执行，保留 `selection/feature_diagnostic5_superseded.json` 标记被添加非LLM控制的v2方案替代，不能重复计数。输入gate显示5/8可消除两组循环（含grammar.residual.s1），另3仍保留；这既不属于LLM/Witness独有能力，也不证明完整调度收益。明细在 `analysis/feature_diagnostic_information_gate_v2/`，原五项未重跑，新增grammar三项回执另列。

## 数据与选择隔离

| 阶段 | 机会库 | 配置 | 用途 |
|---|---|---|---|
| TRAIN | AU/AP，r000/r001 | A/W/E/J，共16图 | 离线证据、候选反馈、联合短名单 |
| VALIDATION | AU/AP，r006 | A/W/E/J，共8图 | 从固定 TRAIN 短名单选择最终程序 |
| TEST | AU/AP，r008/r009 | 8配置，共32图 | 程序与协议冻结后一次正式比较 |
| 最终 TRAIN | 原 TRAIN 四库 | A/W/E/J | 用最终所选程序和统一预算补齐描述 |

统计以独立场景组r008/r009为单位。AU/AP是同组的两类权重/物理机会库安排；同组内的AU/AP、多个约束配置和随机种子不能扩张独立样本数。因此本次TEST只有两个独立场景组，统计结论须保留这一小样本边界，不能用TRAIN胜率替代泛化证据。

LLM首轮b0/b1是分开的冷请求；第二轮同一条件的两批次都收到该条件汇总的16个首轮候选反馈，包含另一批次首轮的表现。因此b0/b1是分列的合成批次，不能视为全程完全独立的统计合成重复，也不能增加TEST的独立n。

配置以西/东站群地面间隔秒数表示：A=(340,340)，W=(1200,340)，E=(340,1200)，J=(1200,1200)；TEST 另有 M=(680,680)、stress=(1800,1800)、MW=(680,1200)、ME=(1200,680)。680/1800及其混合配置未参与**本轮**候选生成、拟合和TRAIN/VAL完整调度选择。卫星间隔固定150秒。同一机会库各配置保持接触节点及原始收益，仅资源约束改变冲突边。实验比较配对静态配置中的完整调度，不冒充尚未实现的求解中途参数事件。

`station_gap` 是根接触所属天线的真实间隔；完整当前图供 typed 图操作访问。实现使用 namespace `heterogeneous_station_local_base9_full_schedule_v1`，不会以全站最小值或均值代替异质约束。

## 真正参与求解的头与共享组件

所有学习头和 classical shared-kernel 头共用完整可行的加权度 seed。每个头在自身构造和破坏—重建阶段实际提交接触选择，公共补全仅填充该合法前缀的剩余可选部分。排序不是记录后丢弃，也不会在每次提交前被另一个 degree 规则覆盖。

冻结预算为2/10 CPU秒；正式种子2/3/5。构造上限占总预算20%，共同交换改进占10%，之后交替破坏16/32个已选接触，活动域上限128。合法 prefix、raw proposal、正收益接受 guard、最佳解轨迹均保存。guard保留当前较好解，但原始负提案不会被删除。

程序结构为 `FeatureRuleProgram`：`name`、`features`、`rule`、`rationale` 四字段。`features` 是 typed 图操作表达式；rule-only 条件不许增加特征。原冻结、LLM feature-rule、LLM rule-only 和 grammar 控制都通过相同实际评分接口执行，包含特征求值费用。

程序是否实际生效应同时查阅 `stats.head_score_evaluations`、`stats.head_commits`、`head_ever_committed`、构造/修复状态及 raw reward。昂贵全图特征耗尽预算后返回合法 seed 是有效的不利记录，不能宣称为该程序的有效排序成功。

## 比较方法和正式来源

| 方法 | 本实现中的含义 |
|---|---|
| Degree、Weight、GRASP | 三种传统排序头，共用同一 anytime 调度骨架 |
| local2swap | 完整图的共同 seed、标准交换改进；不调用条件证据 oracle |
| CP-SAT | 全图布尔 MWIS 模型，原始整数收益，单搜索 worker，共同 seed 作 hint |
| CHILS_ILS | 已发表 CHILS 实现，population=1，线程=1 |
| CHILS | 同一已发表实现，population=4，线程=1；公平单核版本 |

CHILS 的正式会议来源是 Großmann、Langedal、Schulz，*Concurrent Iterated Local Search for the Maximum Weight Independent Set Problem*，SEA 2025，[会议出版页](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.SEA.2025.22)。作者发布的 SEA 2025 软件归档：[Zenodo v1.0](https://doi.org/10.5281/zenodo.15173364)。本实验以冻结二进制 SHA 标识实际执行版本，使用原始64位微秒收益，不取整到秒、不缩放权重。

CP-SAT 的会议来源是 Perron、Didier、Gay，*The CP-SAT-LP Solver (Invited Talk)*，CP 2023，[会议出版页](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.CP.2023.3)。本轮云端 OR-Tools 版本是9.15.6755。经典 shared-kernel 头是透明控制，不冒充上述论文算法的完整复现。

LLM 调用日志保存请求模型、实际可观察模型字段、token使用和原始事件。模型身份不可观察时记为 unknown，不把请求名称当成已证实的服务模型。旧冻结程序是旧算法控制，不计入本轮新 LLM 生成。

## 合成成本与输出接收

12次真实调用消耗 input 395,828 tokens、output 108,914 tokens，合计504,742；其中reasoning output 87,872已包含在output中，不重复相加。缓存读写均报告为0，实际工具活动为0，96/96候选有效；服务模型身份均不可观察。逐调用wall time之和4,027.765秒会重复计入并发区间；从最早开始到最后结束2,174.751秒包含两轮之间训练/反馈等待，不能当作LLM净耗时。无计费凭证，不猜测货币费用。

`llm_calls/<call_id>/response_schema.json`定义原始结构化输出；`response.json`保留原始响应，`validated_bank.v2.json`绑定原始内容、类型/语法接收结果与事件SHA。接收不补槽、不静默替换规则；全部付费候选和重复候选均保留。`generation_cost_all12.json`及[LLM角色与成本说明](README_LLM角色与成本说明草稿.md)给出逐条件成本和局限。索引脚本的`model_calls=0`表示整理时未再调用模型，不表示真实生成次数为零。

## 成本、时限和指标

加载图、共同 seed、全图/局部特征、构造、修复、交换、CP-SAT 建模以及最终可行性验证计入实际 CPU。native 子进程 CPU 单独测量并加入总 CPU，不能用父进程低占用代替其成本。每 worker 固定一个 CPU，8 worker 使用24–31；BLAS/OMP、CP-SAT、CHILS都限制单线程。

2/10秒是**软优化时限**。中断后仍须合法补全和完成可行性验证，因此实际总时间可能略超；记录 `deadline_soft_overshoot`、CPU、wall及 native child CPU。单次完整 JSON 编码费用另有记录；进程启动和最终文件写出不计入优化 deadline。比较表必须显示实际费用，不能把 nominal 2秒等同精确2秒总消耗。

原始收益是微秒 tick 的整数和；除以1,000,000得到秒。主要观察完整可行72小时调度收益、配置改变后的配对表现、同预算强比较方法差距、特征费用和 best-so-far 曲线。不使用局部 certificate 的方向或训练拟合率替代完整调度收益，也不预设所有方法达到全局最优。

## 文件与启动方式

- `freeze_execution.json`：已执行的核、benchmark、native 适配模块及二进制 SHA，以及预算和共同组件；这不是 TEST 程序库冻结文件。
- `banks/frozen_final8.json`、`selection/final_program_ids.json`、`protocol.frozen.json`：VALIDATION后、TEST前的最终程序、准确SHA和正式协议。程序库SHA为 `d81c6b5e996f5748346f346ee187f2edd09dcaa758bcb036d99a57df2629481d`；具体执行源码SHA仍以 `freeze_execution.json`及阶段manifest为准。
- `selection_rule.pre_results.json`、`selection/train_shortlist.json`、`selection/val_selection.json`：预定规则、TRAIN三目标短名单和VAL选择；不能用TEST替换选择。
- `protocol.pre_generation.json`：候选生成前的数据隔离、选择和预算协议。
- `scripts/full_schedule_execution.py`：完整调度与评分实现。
- `scripts/full_schedule_benchmark.py`：单次运行与完整结果保存。
- `scripts/train_candidate_runner.py`：首轮/反馈轮 TRAIN 批量任务。
- `scripts/stage_schedule_runner.py`：VAL、TEST、最终 TRAIN 的注册与执行。
- `scripts/launch_stage.py`：后台启动、独占 `start_receipt.json` 防止重复、stdout/stderr 分开。
- `llm_calls/`、`banks/`、`train_fit/`：离线生成、候选及关系拟合溯源。正式指标需与各阶段 registration 绑定。
- 仓库 `autoresearch/loop-261005-2301/`：只用TRAIN的两轮有限迭代日志，保留128个候选全部Q/G/C、每池四候选端点及handoff；无第三轮。

## 公开输入分卷重建

`review_inputs/manifest.json`给出ZIP整体、按顺序的各分卷及每个NPZ/metadata成员的SHA；该manifest自身SHA为 `9050cd991dfeed522bff66a34c2f1ac2e006cc6ad65ed2596bdd5c40418a2554`。两卷按原始字节连接，不能分别当ZIP解压：part01为50,331,648字节，part02为8,616,825字节；完整ZIP为58,948,473字节，SHA `d755572f53bc917d410e9fce9f67812ebe40c6344206eb545bc9406d52b1ac45`。

```python
import hashlib, json, pathlib, zipfile
p = pathlib.Path("review_inputs")
m = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
archive = p / m["archive_name"]
with archive.open("wb") as out:
    for part in m["parts_in_order"]:
        blob = (p / part["path"]).read_bytes()
        assert len(blob) == part["bytes"]
        assert hashlib.sha256(blob).hexdigest() == part["sha256"]
        out.write(blob)
assert hashlib.sha256(archive.read_bytes()).hexdigest() == m["archive_sha256"]
with zipfile.ZipFile(archive) as z:
    for member in m["files"]:
        assert hashlib.sha256(z.read(member["path"])).hexdigest() == member["sha256"]
    z.extractall("reconstructed_inputs")
```

重建后TRAIN使用 `reconstructed_inputs/train/graphs`；VAL/TEST输入位于 `reconstructed_inputs/heldout/graphs`，由source与metadata split严格隔离。r006的VAL只使用A/W/E/J，不能因为归档中保留了其他输入配置就扩大选优集合。完整输入包可供专家复现，但在训练、反馈和选择程序里不得加载其中的TEST图/结果。

Linux 云环境已观察到 Python3.11.17、NumPy2.4.6、OR-Tools9.15.6755。专家须使用附带的冻结源码和明确的 CHILS 二进制，并让输入图路径与 metadata、manifest一致。

示例：验证集后台执行固定短名单（变量均应指向复现环境的实际路径）。

```bash
python scripts/launch_stage.py --stage val --run-root validation_run \
  --data-root DATA --cipheur-root CODE \
  --program-bank shortlist_bank.json --program-ids-json shortlist_ids.json \
  --protocol protocol.pre_generation.json --execution-freeze freeze_execution.json \
  --budgets 2 --seeds 2 --method degree --method cp_sat \
  --method chils_ils --method chils --native-executable CHILS
```

TEST必须改为 `--stage test`，提供**独立的已冻结协议**、其 SHA 匹配的最终程序库、明确的最终 ID名单，以及 `--budgets 2 10 --seeds 2 3 5`。该协议须含 `frozen:true`、`test_sources`、`frozen_program_bank_sha256`、`final_program_ids`。未冻结会在注册阶段拒绝启动。最终 TRAIN 使用 `--stage final_train`，图根指向原 TRAIN 的 heterogeneous 图目录，另建运行目录。

启动成功只表示 dispatcher 已运行；完成状态以 `results/execution_summary.json`、注册任务数与记录任务数一致为准。`results/jobs.jsonl`、`results/results/*.json`保留逐次完整解、原始阶段提案和异常；所有失败和不利结果交给报告解释，不能静默重跑、过滤或改程序。
