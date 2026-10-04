# V06 held-out verifier：第二次独立静态审查

本次只审查 `scripts/verify_heldout_results_v06.py`、其构造测试及所引用的独立计算 helper、冻结运行器契约。只新增本文，不修改审核器、运行器、原始数据、注册、release 或结果；没有读取正在运行批次的性能内容，没有调用生产调度器、认证 oracle、LLM 或新的科研实验。

审查版本的字节 SHA256：

| 文件 | SHA256 |
|---|---|
| `scripts/verify_heldout_results_v06.py` | `5b5d06672716230f3c6bb9ad87172a3d1dd797571f806d81382dca3539dc965e` |
| `tests/test_verify_heldout_results_v06.py` | `ca0d1b0284dc207a4a50d4b07e2045d8fa2da4a21925c4fea24d47aa87ed342c` |

结论：**独立数值、图和解证明的核心路线成立，但当前 `errors=0` 只能支持已经实际检查的范围，不能称为完整链路、全部预算与所有结果文件的独立审核通过。** 下列三个小构造输入确认了会被接受的缺口；这是审核器覆盖问题，没有推断任何真实批次出错。正在运行的冻结实验无需因此重启。若补强独立审核，应在完整、已冻结的存档上追加新版报告，保留旧源码摘要、审查意见和旧报告。

## 已验证的科学范围

`R2` 范围为 27 个已请求身份、6 个原始/重编号变体、72 个原始状态，即 162 个身份/变体任务、11,664 个状态位置；`EoH` 范围为 4 个身份、24 个任务、1,728 个状态位置。这个脚本审核上述机制与重编号批次，**不审核 V003 全部正式性能实验或 CHILS/M2WIS 等外部原生算法的实现与性能结果**。

审核器及其三个 helper 不导入生产 scheduler/oracle。它独立重建五个按 source cluster 配对共享的双射，运输 F/X、竞争动作和认证顶点字段，并保持区间数值字符串不变；独立计算 demanded/full feature quotient 的有环性、结点/边数及 self-loop requirement 数量，重建所有严格数值预测，并保留 tie/unknown 为无预测值。对于实际保留的解，它检查原图可行性、固定/排除边界、精确收益、共同 Degree 初始解前缀、局部 patch 下界和 clique 上界、正增益提交及最终解。被声明为 restricted exact 的小 patch 另外执行独立精确递推；这属于审核证明，不是新的实验 rollout、原始完整残余认证或程序重选。

完整 72 个 incumbent 存在时，等权 family 的 reward / total graph weight 与 work 宏平均会被精确重算。total graph weight 不是最优值。声明的普通预算停止可保留有效 incumbent；程序/worker 错误和缺失基线应继续保持显式、无 fallback、无伪造零测量。保存的 CPU/wall/work 是执行收据，审核没有重新计时或证明全部操作成本；父进程 CPU 不能解释为所有 worker 的总 CPU。

## 三个已复现的接受缺口

| 优先级 | 位置与极小复现 | 影响与建议 |
|---|---|---|
| P1 | `Audit.kernel`（第 99 行起）：使用现有两结点 toy，`max_patches=1`，提供两个各自合法、零增益的 patch，并使 `patches_attempted=2`。实际得到 **27 checks、0 errors**。 | 核验了声明的 config 相等、逐 patch 合法和最终 trace 计数，但未约束 `patches_attempted <= max_patches`。不能据此声称所有执行预算均独立核验。追加直接的总 patch cap 检查，并分别界定 work/时间 soft overshoot 的可验证范围。 |
| P2 | `pairing`（第 66 行起）：左边竞争 `0/1`，右边竞争完全不同的 `2/3`，仍返回 `strict_reversal`。 | 缺少左右 `(a,b)` 和 cluster 一致性检查；同一 `(pair,query_index,side)` 重复行还会覆盖原行。生产 pairing 已检查动作对齐，独立重建也应拒绝不对齐和重复端点。实际原始认证是否已保证对齐，本次未读真实输入，因此不作结论。 |
| P2 | `Audit.witnesses`（第 88 行起）：有同向量的严格 requirement，即 self-loop obstruction，却提供空 `structural_witnesses`；实际得到 **0 checks、0 errors**。 | 外层四个 quotient 数量/有环字段仍会被独立重算，这个缺口没有否定其数学有环诊断。但保存的 witness 存在性、覆盖及类型数量没有被强制核验，不能称为全部显式 witness/joins 完整审核。至少约束有环时存在合格 witness；若声称逐 SCC/逐类覆盖，应独立重建所声称的覆盖标准。 |

以上复现只调用审核器的 `pairing`、`Audit.witnesses`、`Audit.kernel`，输入为手工构造的两结点对象；未运行任何生产 kernel 或实际 TEST 状态。

## 其余范围和错误处理缺口

1. **身份与 release 深层绑定尚依赖可信准备阶段。** 第 216–226 行检查归档内 artifact/source、root receipt 的自洽关系与本地科学源码一致，但没有完整复核 `execution.registration_sha256`、具体 selection/control/certificate/source 字段、workers，以及 release 所绑定的 prior author/TRAIN 审核与实际 entry roles/program hashes。R2 与 EoH 的 `registration_sha256` 契约不同，不能用同一规则替代。建议与 root 已冻结的注册/release 摘要交叉核验；若保留现状，应明确这些链路是信任已有准备审核，而不是本脚本独立重新证明。

2. **缺失和 worker failure 分支未同等检查全部状态身份。** 第 250–261 行提前 `continue`：null 分支只确认 72 个 `result=None`，未重建全 72 个唯一状态 id/family/cluster/split、coverage 与 null 时间；worker 分支未拒绝夹带非空 interface/summary。正常分支才检查状态身份集合。建议两类分支同样保留并核验全部已请求位置，拒绝重复/遗漏/附加的测量内容；不要为了审核完整性制造测量。

3. **部分完整性字段和汇总文件没有交叉重建。** 当前检查 planned query/status counts 和正常分支部分 coverage，但未审核 `quota_shortfalls`、`normal_budget_stops`/coverage status 分布、terminal marker 的 missing/worker/interface/kernel 计数，以及 `robustness_summary.json` 的五变体 mean/worst、缺失传播和 EoH 六变体质量/work 数组。若后续论文直接使用 robustness summary，这个文件需要独立重建后才具有相应审核范围。现在的报告不能作为该文件已审核的证明。

4. **失败收据仍需区别于实验成功。** `worker_error`、interface error、程序 error incumbent 和 null 可合法导致审核 `errors=0`：这个数字代表审核断言无错，不代表所有科研测量成功。应同时报告正常完成、预算停止、诊断 incumbent、缺失和未测量状态。当前 `kernel_summary` 可对全部保留的 error incumbent 产生数值，应继续明确其诊断范围，不能仅凭非空平均值宣称正常性能有效。

5. **早期异常会中止且不生成统一失败报告。** 缺文件、损坏 JSON、未知身份/变体、非法索引、空 active 上的伪造 initializer，以及独立 exact recursion 的 `VerificationLimit` 可在报告写入前抛出异常。它们没有形成成功报告，因此仍是 fail-closed；但运维上必须把非零退出、报告缺失或 interrupted audit 记为未审核/失败，不能当作零错误。建议追加只记录错误阶段及输入 SHA 的外层失败收据，不重试实验、不覆盖旧报告。`exact_alpha` 是有限 ceiling 的证明程序，达到上限应保留未验证范围，不声称 restricted optimum 已证。

构造测试实际执行了 `tests.test_verify_heldout_results_v06` 的 **8 个测试，8/8 通过（0.001 秒）**。它覆盖了区间不误重编号、共享双射/边、有效 Degree incumbent、错误精确收益、伪造 initializer 分值、严格 reversal、exact tie 和缺失配对端点。它没有调用顶层 `audit()`，也没有覆盖完整归档/release、null/worker/error 各分支、超 cap、缺 witness、配对错位、汇总篡改或 verifier ceiling。建议未来补上述小构造负例；本次遵守只写审查文档的授权，没有修改或添加测试。

本审查不是实际 R2/EoH/V003 结果的通过证书，没有读未完整批次的性能结论，也没有替代独立完整批次审核。
