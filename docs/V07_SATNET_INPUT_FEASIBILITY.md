# V07 SatNet 实际输入可用性与建模边界

2026-10-04。结论：**历史请求数据真实可获取，适合研究持续出现的任务/天线结构及跨周适应；当前不能直接替换 C/W 固定接触 MWIS，也不能声称无损复现原 SatNet。** 本次实际阅读原始 JSON、维护 CSV、字段说明和模拟器源码，仅做输入统计；没有导入模拟器、建图、优化、oracle、LLM 调用或读取 TEST 结果。未知再分发许可的原文件只保存在本地 `.research/v07_satnet_input_audit_001`，本报告及 JSON 仅含字段、计数与摘要。

## 实际获取与正式主源

作者仓库固定于 commit `3e78e56eca1fcd4001c55e7491e6e3eb542e350a`。实际下载的主数据 `data/problems.json` 为 3,569,038 字节，包含全部五个历史周；此外读取 666/646 字节两个小 fixture、69,872 字节维护 CSV，以及短字段说明/模拟器源文件。十二个原文件合计 3,761,396 字节；没有克隆仓库、批量下载其他语料或运行其训练框架。

- [作者项目及正式参考](https://github.com/edwinytgoh/satnet)。项目链接其 [IEEE Aerospace 正式论文](https://ieeexplore.ieee.org/abstract/document/9438519/) 和 [AAAI ML4OR 主源论文](https://openreview.net/pdf?id=buIUxK7F-Bx)；这里没有引用 arXiv。
- [固定版本字段说明](https://github.com/edwinytgoh/satnet/blob/3e78e56eca1fcd4001c55e7491e6e3eb542e350a/data/README.md)、[主 JSON](https://github.com/edwinytgoh/satnet/blob/3e78e56eca1fcd4001c55e7491e6e3eb542e350a/data/problems.json)、[维护 CSV](https://github.com/edwinytgoh/satnet/blob/3e78e56eca1fcd4001c55e7491e6e3eb542e350a/data/maintenance.csv)。这些链接支持原始字段；下列数值由本次读取原字节统计，未从论文表中抄取或按其四舍五入数补齐。
- 仓库根目录及已读取文档没有 LICENSE；未建立代码/数据再分发许可。公开可读取不等于明确许可。本次仅报告 schema/计数/哈希，未将原请求文件放进共享数据目录。

## 全五周的实际内容

|2018周|请求|任务来源 subject 数|有窗口的物理天线|非空资源组合|窗口记录数|不同资源/时间窗口|请求小时总量|含多天线备选的请求|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|10|257|30|12|39|2,513|1,438|1,191.5|21|
|20|294|33|12|27|2,949|1,604|1,406.5|19|
|30|293|32|12|49|3,108|1,939|1,464.0|25|
|40|333|34|12|39|3,370|2,092|1,736.7|25|
|50|275|29|12|42|2,759|1,499|1,292.2|23|

窗口记录属于“某请求可使用某资源的视窗”，不是已确定的通信轨道。相同资源/时间窗口会出现在不同请求中；去重后的窗口数不能作为请求数，全部窗口记录数也不能直接当作 MWIS 任务节点数。总计 1,452 个请求、14,699 条窗口记录，仍只有五个原始周来源。

`resources` 与字典键的并集声明 14 个物理天线身份，但每周**非空窗口只涉及 12 个**，与 `initialize_antennas` 的十二资源相符；所有非空窗口都使用已配置天线。不可把 14 个声明值等同于可用容量。第 40 周当前原 JSON 的 `subject` 基数确为 34，主源论文表为 33；保留实际固定版本差异，不静默改成文献数字。维护文件共 1,798 行、12 天线；对应五周标记行数分别 37/31/35/38/41，这是原 CSV 的周字段统计，实际模拟器按时间过滤/裁剪后才产生可用区间。

每周时间范围均为 ISO 周一 UTC 零点至下一周一 12:00；例如第10周为 `2018-03-05T00:00Z` 至 `2018-03-12T12:00Z`，第50周为 `2018-12-10T00:00Z` 至 `2018-12-17T12:00Z`。这不是七日纯窗口；源码明确有十二小时尾部 padding。所有十对周块时间范围互不重叠，原 `track_id` 集合交集为零，但物理天线重复、任务来源明显复现（例如第10与第50周有26个共同 subject）。适合时间外推，不是五个独立同分布随机种子。

可以预声明前10/20/30周 TRAIN、后40/50周 TEST；这将有3个训练周和2个测试周，周内派生窗须保留同一 source-cluster，不得当独立周重复。这是尚未冻结的可行划分建议，本次没有选择/构造实验样本。若要求大量独立未来时期，这个五周静态集合不够；重复训练种子、切小窗或复制请求不能补出新的独立周。

## 字段与单位：实际 schema

|层级/字段|实际含义|适配要求|
|---|---|---|
|根键 `W10_2018` 等|每周对应请求列表|来源周整体分组，不能随机混合同周派生图|
|`subject`, `user`, `track_id`, `week`, `year`|任务来源、任务类型、请求身份、历法来源|`user` 在原 scheduling 任务未使用；不能发明优先权|
|`duration`, `duration_min`|要求及最低总通信时长，**小时**|原 `ProbHandler` 乘3600并转 int32；不是节点预定时长|
|`setup_time`, `teardown_time`|请求自己的准备/撤收时长，**分钟**|乘60；这不是 C/W 固定20秒跟踪余量|
|`time_window_start/end`|请求允许时间范围，UTC epoch秒|与 ISO 周一减偏移，并保留 padding 契约|
|`resources`|一组备选，每个备选又是需要同时占用的天线集合|不能将组合字符串作为一个互不相交的“站”|
|`resource_vp_dict`|资源组合到可用视窗列表|组合存在共享物理天线；空列表仍须保留|
|视窗 `TRX ON/OFF`, `RISE/SET`|原窗口边界秒值|原 `ViewPeriods` 使用 TRX ON/OFF、转相对秒并裁剪；RISE/SET不是另一个奖励|
|维护 `week/year/starttime/endtime/antenna`|不可用活动区间，时间为 epoch秒|准备和撤收也须避开维护|

每周请求时长范围均为1–10小时、最低时长1–8小时。准备时间通常30/45/60分钟，原始数据也有90/120分钟；撤收通常15/40分钟，也有60分钟。原数据没有卫星轨道元素、经纬度或可直接使用的固定“星地 contactstart/contactend/reward”三元组；有 mission/antenna/window 元数据，场景信息明显强于普通 MWIS 文件。

`small_longVP_prob.json` 与 `smallest_array_prob.json` 是两个小相对时间 fixture：schema 不含主数据的 `resources`，其视窗也不都有 RISE/SET；一个有 `DURATION_HRS`。因此不能将小 fixture 时间与历史主数据 epoch 混用，也不能把它们作为新的独立大规模场景。主数据第50周有3个 `duration_min` 小数在按原十进制文本精确换算时不是整数秒，而旧浮点乘法/int32会截断；若复用原任务，应固定原换算契约，不能悄悄改权重或时长以制造优势。

## 与当前固定接触 MWIS 的关系

以下来自实际阅读 [ProbHandler](https://github.com/edwinytgoh/satnet/blob/3e78e56eca1fcd4001c55e7491e6e3eb542e350a/satnet/simulator/prob_handler.py)、[模拟器](https://github.com/edwinytgoh/satnet/blob/3e78e56eca1fcd4001c55e7491e6e3eb542e350a/satnet/simulator/scheduling_simulator.py)、[天线管理器](https://github.com/edwinytgoh/satnet/blob/3e78e56eca1fcd4001c55e7491e6e3eb542e350a/satnet/simulator/antenna_manager.py)、[ViewPeriods](https://github.com/edwinytgoh/satnet/blob/3e78e56eca1fcd4001c55e7491e6e3eb542e350a/satnet/simulator/view_periods.py)；没有执行其函数。

1. **选择的是请求及可调轨道。** 原过程从当前可用窗口选择资源，必要时裁剪轨长；默认左对齐，源码还提供中心/右/随机对齐。不同已排活动会改变可用窗口及可放置 start/end。同一 VP 不能直接当作全部通信时长都可计奖的固定任务。各周多数 VP 比请求时长长；例如第10周2,007/2,513条，比最低时长短的窗口也保留115条。
2. **占用包含准备和撤收。** 天线分配的是 `[trx_on−setup, trx_off+teardown]`，而通信奖励只含 TRX 时长。组合活动逐一占用每个物理天线。当前把一个组合放进 `Contact.ground` 字符串，只比较字符串相等，会漏掉部分共享天线的冲突。
3. **存在跨活动请求约束。** 原默认 `allow_splitting=True`，要求时长≥28,800秒进入拆分逻辑，单段最低条件及已服务/剩余总时长随状态变化。源码维护未完成拆分请求，并会撤销无法完成的组合。第10/20/30/40/50周有77/105/122/154/98个请求达到八小时阈值。仅给每段独立正权重、加两两时间冲突，会允许不满足最低总量或超过请求总量的组合。
4. **同任务来源还有通信重叠控制。** `remove_mission_overlaps` 按已排 mission transmission track 缩短/分割候选 VP。这可以在固定活动模型中成为同 mission 的两两边，但原过程是动态轨道，不是当前静态 VP 图。
5. **容差及维护属于原契约。** 默认维护开启；`tol_mins` 默认0，代码某些注释写10分钟不能代替实际配置。输入适配必须固定 padding、单位转换、容差、维护和拆分，不能借更换这些条件制造改进。

因此有两个不同工作量的路线：

- **原 SatNet 任务路线：** 保留原连续/秒级可变轨长、组合天线、拆分总量、维护及奖励。需要新的真实 action/boundary 接口和证书实现；目前 Graph/Contact 与固定权重 MWIS 完成值不能无损承载。不是换一份 CSV 就 ready。
- **SatNet-derived 固定活动路线：** 先以不依赖求解结果的规则冻结合法完整请求活动备选，包括可选的完整拆分 bundle。每个 bundle 内先检查最低/最高总时长及各段合法性，节点权重为实际通信秒数；同请求备选互斥，共享物理天线的扩展活动冲突、同 mission 通信重叠均编码为边，维护作为节点有效性。这样可准确表示**冻结备选集合内**的选择问题。有限锚点/轨长备选未覆盖原可变调度空间，所以不能称原 SatNet 无损 MWIS 化。只保留不可拆分任务也是明确的任务限制，须给出覆盖与排除数量，不得伪装为完整 benchmark。

## 配置适应能做什么、还缺什么

数据具有真实重复的任务来源/天线竞争和未来请求周，支持配置适应的背景。不同 gap context 应共享同一冻结机会/完整活动备选、相同通信秒权重、同一需求与维护来源。不得改变边或奖励去逼出算法优势。

但是原字段提供的是**每请求准备/撤收时间**，没有 C/W 中统一的 `ground_trans_time`、`satellite_change_time` 或 `satellite_trans_time` 校准。可以研究额外天线 changeover clearance 或准备配置的干预，但必须先明确物理含义和来源，说明它如何影响资源占用；若也改变维护下的节点有效性，就必须记录 context-specific unary exclusions，不能宣称只有两两边改变。原代码的拆分/容差开关也不等价于“同机会 onlygap”，不可拿来偷换任务。

未来重复结构只支持 transfer 的必要背景，不证明 exact base9 alias、严格反转或质量收益。场景冻结后仍先做 TRAIN 内部因果链诊断：证据位于实际决定边界、feature gate与scalar margin区分、rank确实改变action/searchpath、共同solver预算是否已消除差异。V06 TRAIN品质平局发生在分布转移前；换 SatNet 或变大不能自动归因/修复这点。

**实际可用性判断：** SatNet 值得保留为后续有真实任务语义的外部场景，当前仍需较明显接口重构，且静态五周仅支持有限时间外推；现有本地 C/W 的固定时长/约束语义更接近当前研究接口。普通公开 MWIS 图可保留为 secondary 求解器兼容与质量比较，不能证明卫星配置适应。CelesTrak则是推导 visibility 的轨道输入源，仍是 derived contact simulation，不是直接调度 CSV。

## 小型来源 profile

- `experiments/analysis/v07/satnet_input_profile_001.json` SHA256：`02002ffe80606be21ecce0bbb2c2f501ea86dff5ea49bf3d025fc2016d87fe72`。
- 主 `problems.json` SHA256：`8ea0ef080729cd51867744b095f59f856b2cb6acb7e564b9b8fb9c5721833f98`。
- `maintenance.csv` SHA256：`c4facfae8ece7c25c794d255a5a0bb358061ed193461410a3d3e569fa06dff6c`。
- JSON 保留所有十二原文件 URL、字节与SHA、五周完整 schema/types/单位/时长范围、维护分布、十对周交集及两个 fixture 差异；不导出原 mission/antenna/track身份，不含效果结果。

本次未修改 V06、原输入或任何已冻结协议。V07 场景及 SatNet 适配仍未冻结、未启动；用户已广泛授权研究工作，无新增许可流程。
