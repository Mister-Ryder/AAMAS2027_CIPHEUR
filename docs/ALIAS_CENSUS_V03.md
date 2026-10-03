# V03 开发域精确输入别名清点与定向证书查询

日期：2026-10-03。实现：`cipheur/alias_census.py`；测试：`tests/test_alias_census_v03.py`。本报告先记录已完成的本地 **census-only** 结果。服务器的定向 oracle run 由 root 在独立不可变 source snapshot 上执行；其最终 bounds/quotient 尚待审阅，不在这里预先给出证书结论。

## 目的与边界

原先自然时序/C3 商图无环，是对少量 acquired specifications 的结果，不是对所有自然动作都不存在信息别名的证明。本扩展在已完成的开发数据上枚举所有共同冲突对，先测量完整基础输入的精确别名和跨侧连接，再用预先确定的至多 200 条 query plan 查询 sound 条件上下界。它既可能发现自然信息阻碍，也可能说明别名存在但条件价值相等，或预算仍无法判断；三种情况都必须保留。

只使用 `development_scale_001.tar.gz` 内唯一的 `development_scale_001/data.json`，读取 train 与 validation 两个容器，拒绝 test/transfer/outcome 容器。排除 family 为 diagnostic、来源为 designed probe 或 population 标注为 mechanism diagnostic 的记录。没有读取 hold-out/transfer 结果，没有修改候选 bank、冻结 programme 或主文。小单元测试中的反例全部是人工 fixture，不作为自然研究结果。

源 data SHA-256：`7ec32a0ebf0588c1f8fd8b3b522975c0743d84be53bb05ecb5d00bb8b9db5342`。开发归档 SHA-256：`578621817ba4ff99297a288da80d4d1d0e50e70b3fff335677966e3be1674ad9`。本地清点执行记录在 `.research/alias_census_local_001/`，对应清点源码 hash `cb68c81e41dca9d6a1043a776f7e6926b747e31148b4c556d0c1d748c6896839`。随后仅为完整查询增加了逐行 flush/进度/partial 状态记录；root 的运行保留它上传时的不可变 source snapshot 与 execution receipt，不能把两个 source hash 混称一个执行版本。

## 实际可见输入与实际边界

基础向量直接调用当前 `FeatureRuleProgram` 的 `_FeatureState.feature_values`，不是旧 `programs.features` 的普通 `sum`：

`weight, duration, degree, conflict_weight, max_conflict_weight, compatible_weight, station_gap, satellite_gap, remaining_count`。

聚合沿用当前 typed evaluator 的排序与 `math.fsum`。Exact equality 使用现有 `vector_key`，按整数/二进制浮点的精确 `Fraction` 比较，没有容差、分箱或舍入制造别名。全部九项都参加比较；不能因为本次 incumbent rule 只用了 weight/degree 就删掉另外七项。

incumbent 固定为 `weight / max(1, degree)`，按分数降序、contact ID 打破动作 tie，与 feasible constructive kernel 一致。左右各执行初始及至多两个真实选点后的边界；同一 pair 中相同 fixed/excluded 集合合并。将 **相同 B** 重放到左右，保留两侧都可行的边界。候选 a,b 必须同在两侧 available、且同在两侧冲突。actual boundary 是 incumbent 产生的；候选对枚举所有 common conflict edges，不要求其中一个恰好是下一次 argmax。因此这是补充的 alias census，不应伪装为原先所有 query 都 anchored argmax 的 acquisition 条件。

实际 rollout 不因别名或 oracle 标签改变，没有构造对方法有利的 incumbent。两处在另一侧不可行的重放单独记录，而不是丢掉分母后声称全部重放成功。

## 别名类别与 oracle 前选择

每个有效边界枚举完整 common conflict edge 集合，记录以下集合及其交叠，不能相加当作互斥类别：

1. **同侧 exact alias**：左右任一侧的九项向量 a=b；只要该侧条件值能证明严格不同，就足以得到一个 strict self-loop，不需要另一侧也有 strict 结论。
2. **同侧 typed structural distinction**：在 exact alias 上，当前类型化操作的 neighborhood edge count、edge-min sum、edge-product sum、clique-cover weight 或 deterministic greedy weight 至少一项不同。这里的区别是实际数值操作，不是把 contact ID 或任意颜色当结构特征。
3. **跨侧 direct/swap matches**：aL=aR 且 bL=bR，或 aL=bR 且 bL=aR；前者可能在 reversal 时闭成二环，后者可能在 preservation 时闭成二环。也记录任意单个跨侧 endpoint 相等连接，并在取得关系后重建全部查询 evidence 的 quotient，允许发现更长环。

若 active 集合与 active induced edges 在两侧完全相同，则条件优化问题相同；没有同侧别名的 cross-only 对不能单独产生 reversal 二环，因此保留清点记录但不花 oracle 预算。这不证明它们在与其他 occurrence 联合后永远不能参与长环；本扩展不能据其未查询宣称全局没有所有可能的信息矛盾。

query plan 在调用 oracle **之前**写出：优先全部 typed-distinguished within aliases，其次其余 within aliases，再 cross swap/direct/partial joins；每层按 pair/split/boundary/action identity 的 SHA-256 ID 排序，最多 200 条。没有 oracle outcome 参与排序或删选。这是针对疑似信息冲突的确定性设计，不是 200 个均匀独立抽样；不得把其 label 比例当作全体自然 workload 发生率。

## 未暴露的配置字段必须单独审计

当前 typed base 将 `station_gap`/`ground_trans_time` 映为 station_gap，将 `satellite_gap`/`satellite_change_time` 映为 satellite_gap，但 **没有显式 satellite_trans_time 字段**。因此该参数变化时跨侧 vectors 相等，并不证明只有新的 graph structural feature 才能解决问题；添加当前遗漏的配置字段可能已经足够。

每条 candidate 保存 unexposed_changed_parameters。证书汇总建立两个 exact quotients：当前九项 base，以及追加遗漏 numeric configuration fields（含字段是否存在标志）的审计向量。若九项 base 有环、加配置字段后 DAG，则只称**当前基础接口有信息阻碍，可由显式配置修复**，不能称纯 structural necessity。若同侧 strict self-loop 成立，同侧配置值对两个动作相同，追加该配置不会消除 self-loop；这是更直接的同侧信息证据。追加配置后的 DAG 同样只限定有限 evidence，不能证明自然输入已经充分或 bounded DSL 可实现。

此审计不修改部署 `FeatureRuleProgram` 或 frozen banks；它是检测保证范围的反证检查。

## 已完成的本地清点结果

数据含 190 开发 pairs；排除 40 probes 后保留 **150 pairs / 300 graph contexts**，规模 32–1,024。左右初始+两步共产生 900 proposed boundaries，去重为 550；548 可双侧重放，2 不可。结果是选择的 incumbent 与前两步范围内的描述性清点，不是所有 reachable schedule states 的普遍定理。

| 域 | Pairs / contexts | 有效 distinct B | Common conflicting pairs | 同侧 exact aliases | Typed-distinguished aliases |
|---|---:|---:|---:|---:|---:|
| C3 | 30 / 60 | 91 | 368,346 | 26 | 9 |
| Temporal balanced | 40 / 80 | 150 | 25,203 | 0 | 0 |
| Temporal ground-scarce | 40 / 80 | 173 | 45,693 | 9 | 0 |
| Temporal satellite-scarce | 40 / 80 | 134 | 34,502 | 6 | 0 |
| 合计 | 150 / 300 | 548 | **473,744** | **41** | **9** |

41 按 pair-boundary-action 对计数，左右若都 alias 只算一次；分侧 L=41、R=34，不能将它们相加当成 75 个不同候选。41 条出现在 **10 个 distinct pair instances、14 个 distinct contact-action pairs**；9 个 typed-distinguished 条目则来自 **3 个 C3 pair instances、3 个 contact-action pairs，各三个边界**：`c3_train_256_0001`、`c3_validation_256_0001`、`c3_validation_1024_0002`。这是三个来源子问题，不是九个独立样本，也不是三个独立物理 constellation 来源。

按 common pair-boundary 分母，exact aliases 约 0.00865%，typed-distinguished 约 0.00190%。域大小/密度及重复边界决定该分母，C3 占大部分 pair 比较；这些是清点比例，不给 population CI。**实际无 candidate 的有效边界是 491 个**；数值以 census.json 为准。自然 alias 确实稀疏但非零，故“自然无环”必须保留为原证据集的结论。

跨侧 direct match 119,839，swap 6，任意 cross join 120,334；全部 cross matches 来自 C3（temporal 的显式 station_gap 变化使完整向量跨侧不同）。所有 category 合并有 120,369 candidate pair-boundary 条目，其中 81,961 是没有同侧 alias 的完全相同残差 cross-only 问题，不查询；程序定义的 query eligible 38,408。固定 query plan 选中 200：9 typed within + 32 其他 within + 159 cross direct；eligible 中余下 38,208 未查询。所有 within aliases 均纳入本次 query plan，但并不意味着已经全部得到 strict label。

本地 census 耗时 60.8 秒；没有对这些自然候选运行 oracle。3 个 C3 structured alias 是否拥有 sound strict requirement，仍等待服务器完成结果。**目前不能写“发现自然 contradiction”，也不能因没有 label 写“证实自然无 contradiction”。**

## 查询预算与 sound label

默认每个 candidate 用独立 Budget：2,000 expanded nodes、64 conditional calls；每次 induced solve 500 nodes，progressive region 上限 1,024，epsilon=1e-8，verified weighted-clique-cover envelope。也可用较小的 500–2,000 total-node budget，但须把值写入 execution receipt。节点/call cap 不约束所有 clique construction、exact arithmetic 和 IPC 的时间；真实 elapsed 另报。

调用现有 `certify_pair(include_preservation=True, raise_on_exhaustion=False)`，所有 raw/accumulated exact bounds 与 complete feasible lower witness 保留。strict side preference 只由该侧 L>other U+epsilon 导出。两侧都 strict 且方向相同才叫 preservation，不同才叫 reversal；任一侧 unknown，则 pair_relation **unknown**。已证明的一侧可以单独作为 sound arc，但不能把另一侧未知伪造成 preservation 或 reversal。

汇总重建全部已证明 side arcs 的 exact full quotient，包括 self-loops 和 concrete equality joins。预算停止、exact tie、region limit、尚未查询及 replay invalid 分开保存。DAG 只说明这些已取得关系没有矛盾；它不能给所有未查询或 unknown 候选作负面标签。

## 运行与产物

服务器已有完成开发数据时：

```text
python -m cipheur.alias_census --data runs/development_scale_001/data.json --out runs/alias_census_001 --workers 4 --max-queries 200 --query-nodes 2000 --nodes-per-call 500 --max-region 1024
```

仅本地清点：

```text
python -m cipheur.alias_census --archive experiments/runs/v03/development_scale_001.tar.gz --out .research/alias_census_local_001 --census-only
```

输出目录必须新建/为空，避免覆写旧来源。产物：execution.json（输入/源码哈希与允许 splits）、census.json（全部分母、分层、边界出处/无候选/invalid）、candidates.jsonl（全部候选与 exact vectors）、query_plan.json（oracle 前固定 IDs）、oracle_results.jsonl（每条预算/上下界/未知/证书）、summary.json（两种 full quotient 与计数）、complete.json。后续 I/O 改进版逐条 flush query results、每十条输出进度，中断时保留 partial；root 已运行的不可变版本不在途中覆写。

## 源码审查与小案例验证

十项独立单元检查通过，本次最后执行 0.200 秒，覆盖：

- typed fsum 与全部九字段，直接禁止旧 `programs.features` 被调用；包括 `1e16+1+1` 的非结合浮点求和差异。
- development-only 容器、diagnostic/source probe 排除、重复 ID、split guards。
- 30 个小随机图，对全部 unordered pairs 独立枚举 common edge/左右 exact alias/union 分母。
- 独立重演 actual weight/degree rollout 与 ID tie break，以及另一侧新增冲突引起的 invalid replay。
- query plan 对列表重排不变、优先级与不调用 oracle。
- 八节点合成 fixture 的 full conditional optimum 穷举对照，核对每个 saved bound 及 feasible lower witness；同侧 alias 得到真实 strict self-loops。
- 左侧已 strict、右侧因 max-calls=2 未计算的情况仍为 pair unknown，只留一条 proved arc。
- satellite_trans_time omission 产生跨配置二环，但显式 audit field 消除；拒绝将该例称为纯 structural necessity。
- 完全相同 residual 的 cross-only 对保留分母但不查询，以及两 worker 与串行的 IDs/labels/node count 一致。

测试不替代 bound 的数学证明：exact feasible L 与 verified clique/induced MWIS U 的保证继承现有 oracle；自环/环的不可满足性继承 full-vector strict quotient 命题。本模块的新增保证是：没有用 proxy 当 label，没有删掉可见输入或用容差伪造 alias，候选选择不看 oracle outcome，单侧未知不变成稳定偏好，未暴露的配置字段不会被混称为结构必要性。

## 完成后主文应如何使用

主文可先把自然零环限定为原 acquisition，增加精确别名清点的 **41/473,744、9 条来自 3 C3 pairs** 和已声明 boundary 范围。服务器结果完成并核验后，补充这些候选中的 proved side arcs、reversal/preservation/unknown、两种 quotient 是否矛盾和 concrete witness；若 unknown 多，明确不能排除矛盾。若只有 omission cycle，报告 explicit configuration 解释。若得到同侧 strict self-loop，用一个真实 C3 pair 的原始 IDs/边界/完整九项相等向量/结构数值/严格上下界构成可复查见证，另外两个边界作为重复，不膨胀独立样本。

这项扩展是 **development information-incidence study**，不参加已冻结 programme selection，不称独立 test，也不从结果挑下一批有利实例。完整清点、哈希、候选与 bounds 留在 MD/归档；最关键的自然实例数量、unknown 状态与是否需要显式配置应进入主文。
