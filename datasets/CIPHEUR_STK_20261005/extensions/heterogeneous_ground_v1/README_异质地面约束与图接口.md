# 异质地面约束：冻结窗口上的 west/east 因子设计

本候选采用原 P0 的 4 个完整机会库，49,882 个接触；不新增轨道、可见性计算、任务、区间切片或收益。每星/每天线容量仍为 1，卫星 gap 固定 150 秒。地面站分组在生成标签前按原坐标确定：west 为经度 88/94/100 度的 6 站，east 为经度 106/112/118 度的 6 站。

| 因子 | west 每天线 gap | east 每天线 gap | canonical tag |
|---|---:|---:|---|
| A | 340 s | 340 s | gW0340_gE0340_s0150 |
| W | 1200 s | 340 s | gW1200_gE0340_s0150 |
| E | 340 s | 1200 s | gW0340_gE1200_s0150 |
| J | 1200 s | 1200 s | gW1200_gE1200_s0150 |

各 gap 是开发配置值。参数向量保存在 `source_plan/extension_parameters.json`。A/J 复用原 P0 的 g340/g1200 图数组；W/E 由独立纯函数 `build_per_antenna_edges` 按各天线实际 gap 构造。所有同源图的接触、资源、原端点差收益和节点映射哈希保持一致。

## 输入统计

| 机会库 | mA | mW | mE | mJ | west 新增边 | east 新增边 | 跨组卫星冲突 / 两端暴露 |
|---|---:|---:|---:|---:|---:|---:|---:|
| CP-AU-r000 | 84,132 | 106,433 | 106,489 | 128,790 | 22,301 | 22,357 | 24,390 / 24,390 |
| CP-AP-r000 | 80,313 | 103,349 | 103,431 | 126,467 | 23,036 | 23,118 | 24,444 / 24,444 |
| CP-AU-r001 | 84,287 | 106,643 | 106,644 | 129,000 | 22,356 | 22,357 | 24,494 / 24,494 |
| CP-AP-r001 | 80,289 | 103,291 | 103,358 | 126,360 | 23,002 | 23,069 | 24,473 / 24,473 |

两个地面轴均实际新增冲突边，满足 `E_A⊆E_W⊆E_J`、`E_A⊆E_E⊆E_J` 和 `E_J=E_W∪E_E`。west/east 新增边的交集为 0。同一个接触只属于一副天线和一个组，故同节点 mixed new-edge wedges 为 0 是分组的直接结果，不能据此判断调度优化没有交互。

现有跨 west/east 的同卫星冲突边连接两个组的决策。表中“两端暴露”只统计此类边的两个端点分别 incident 于其所在组新增地面边的数量。四库中所有跨组卫星边均满足该输入条件。这是 coupling exposure，既不是独立样本数量，也不是已证明的条件偏好或优化收益。

## 必须使用的实际参数接口

JSON：`graphs/<source>/<tag>.json` 包含 `station_gap_mode="per_antenna"`、`station_gap_by_antenna_seconds`（340/1200 的整数秒值）、`antenna_group` 和 `satellite_gap_seconds=150`。

NPZ 保留原顶点、时间 tick、CSR、边与 edge mask 字段，并添加：

- `ground_gap_by_node_ticks`：每个根接触对应天线的实际微秒 gap。
- `ground_gap_antenna_ids` / `ground_gap_antenna_ticks`：完整映射的并列数组。
- `antenna_group_by_node`：west/east。
- `station_gap_mode`：per_antenna。

不提供 `ground_gap_ticks` 全局标量，也不填均值、最小值或 0。完整 base9 的 station_gap 必须取根自身天线的真实映射值。原 global-scalar `_FeatureState` / `CompiledEvaluator` 需要扩展适配器，不能不作适配直接评分。实际 evidence 适配器采用 `heterogeneous_station_local_base9_v1`：station_gap getter 返回 340/1200 的整数秒值，保持原评分表达式的除法类型；Fraction 秒值用于端点、收益和证书的精确算术，邻域收益聚合保持实际执行接口的二进制 `math.fsum` 语义。本输入筛选使用独立命名空间 `exact_microtick_local_antenna_gap_base9_v1`，不得把其整数坐标直接当作实际执行向量的键。

## 实际精确等值连接

在所有顶点活动且 `F=X=∅` 的范围中，完整 base9 精确满足：

- west 根：A 与 E 的向量相等，W 与 J 的向量相等。
- east 根：A 与 W 的向量相等，E 与 J 的向量相等。

这是因为其他站组改变的地面边不改变根的邻接集合、自己的 gap 或活动顶点收益。完整 base9 不读取远处边的排列。16 图共有 199,528 个发生项，得到 99,764 个不同向量与 99,764 个大小为 2 的跨配置等值类。

等值连接本身不证明表示矛盾。只有同一声明边界下 sound 条件偏好与这些精确连接组成 self-loop/cycle，才构成实际 G2 信息障碍。该结论由 evidence 组的四侧证书与完整 demanded quotient 决定；本阶段没有调用 oracle 或 LLM。

机器结果位于 `analysis/heterogeneous_graph_summary.json` 与 `heterogeneous_graph_screen.csv`。每源 `node_axis_degrees.csv` 给出 dW/dE 和两端暴露的跨组卫星边度，供后续绘图。原 340/1200 阈值的敏感性结果可继承 P0 已完成的针对性检查，本构建过程未启动 STK。

构建入口为 `scripts/build_heterogeneous_graphs.py`。其纯工具依赖本数据根目录的 `scripts/build_graphs.py` 和 `extensions/joint_resource_v1/scripts/build_joint_graphs.py`；完整传阅包需一起保留，原文件均未修改。
