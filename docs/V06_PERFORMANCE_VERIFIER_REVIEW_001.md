# V06 正式性能审核器：独立只读审查 001

审查日期：2026-10-04。授权范围为 `scripts/verify_performance_test_v06.py`、其构造测试、独立数学 helper、冻结运行器的静态契约和已经冻结的注册 metadata。只新增本文，不修改审核器、运行器、注册、release、科学源码或实验结果。没有调用顶层 `audit()`，没有读取进行中或未终结批次的性能内容，没有运行生产 kernel、原生 solver、认证 oracle、LLM 或新的实验。

结论：**完整请求 frame、原图精确目标、原生算法收据和保留 incumbent 的局部证明重建路线成立；构造测试通过。审查期间 root 已进一步补强文件容错、warm 前置条件和阶段成本，修复状态按下文 SHA 分段记录，以末尾补记为最新状态。`errors=0` 仍不等于全部执行细节与时间成本的独立证明。** 这里没有判断任何实际批次是否出错，也不是 V003/R2/EoH 实验通过证书。补强应针对已冻结完整存档追加审核，保留旧报告，不重启科研实验。

## 字节版本与本次实际验证

源码在 root 改善期间发生变化，故分开记录观察与执行版本，避免把新修复追溯为旧版已经通过。

| 阶段 | 性能审核器 SHA256 | 性能测试 SHA256 | 本次行为 |
|---|---|---|---|
| 最初静态读取 | `ddfc47a6e2656ee9eca9b98249f4b1e5c691abfc84af4b3dd23febf8e0d3210e` | `6c7f7d330228e1b58a88b186b6ba49b574e33a32067154c39a4f5458702753af` | 静态阅读；不据此声明后续 probe 的执行版本 |
| 初版 probe 与 9 个原测试 | `136b3b0444336399e6dc86c851ccbf2cafc47aee3a7e9bb6a4d500aaa47e2044` | `6c7f7d330228e1b58a88b186b6ba49b574e33a32067154c39a4f5458702753af` | 执行前后源码 SHA 一致；9/9 构造测试通过，另复现下文 3 个接受缺口 |
| root 第一次修复后观察 | `0d6d5c0be89e91d8a42b4b7a3eda0314e619afad8ea837335f2187a171011df2` | `849a48dc8de44f39cf9c9285cbe3feefa868f3b182acb97fb62b146286090d8d` | 静态读取修复内容 |
| 本文首轮复审、27 个测试执行版本 | `26ee941b0e945db2ab693ac814ca1b93694f037502573836320a747828afdab6` | `849a48dc8de44f39cf9c9285cbe3feefa868f3b182acb97fb62b146286090d8d` | 14 个性能 + 13 个 held-out 构造测试全部通过；执行前后 SHA 一致 |

实际运行的是 `python -B -m unittest tests.test_verify_performance_test_v06 tests.test_verify_heldout_results_v06 -v`；27/27 通过，测试报告用时 0.003 秒。输入全为手工两结点图、伪造收据或构造 frame。此时间是审核测试时间，不是算法实验时间。未运行完整归档解析/审核，未证明当前实际 52,548 行结果均通过。

独立 helper 的本次观察 SHA：

| 文件 | SHA256 |
|---|---|
| `scripts/verify_public_alias_v05.py` | `6b349b659bad3acfd3a9e1abbf9046a984f8f66df05068841c1ba8c076aa959a` |
| `scripts/verify_matched_llm_v05.py` | `52b331fea2214642ac50ffe3996c95a6fb9893320e50df84e1371f8fedae087b` |
| `scripts/verify_synthesis_train_v06.py` | `941264da65d8aac3ccb9242de75ebff4c7f8cc29eb602e071be11d4e25dc8322` |

## 冻结科学范围与正确解释

审核器固定到 `experiments/discovery/performance_r2_eoh_test_v06_003_registered_001`。本次仅阅读其冻结协议、deployment、input freeze 和 context inventory，未读 solver outcomes。冻结 frame 为 302 个上下文、三个 nominal wall target（0.1、1、5 秒）、每个 context/target 的 11 个原生算法请求、1 个共同 CHILS-half initializer、23 个 cold 策略位置和 23 个 warm 策略位置。因此共有 `302 × 3 × (11 + 1 + 23 + 23) = 52,548` 个请求位置。

23 个策略身份包括 4 个 genuine W joint、12 个非 guarded W/R/O quality comparator、2 个固定 quality control、4 个单独冻选的 EoH-DSL quality 身份和 Degree。冻结 deployment 的 23 个位置当前均 available，缺失为 0。审核器仍需要守住一般缺失契约；下文旧版 missing probe 是潜在边界，不能暗示实际冻结身份已经缺失或被 fallback 替换。角色不应合并，EoH seed-retained origin 不能改称新 genuine proposal 或 joint-gate winner。

302 个上下文包括 216 个六类新调度实例、25 个 WDP、3 个 UAI Segmentation、10 个 UAI Grids CHILS64，以及 24 个 C3 interval exploratory 和 24 个 C3 legacy exploratory。后两类此前已暴露，保持 exploratory 身份，不能重新称为盲 TEST。总 graph weight 是可行目标的归一化分母，不是最优值或 TEST 内挑选的最佳算法分母。

原生算法为 CHILS、CHILS-ILS、M2WIS 各三个固定 seed，以及 Struction、WeightedBR 各一个 seed。审核器独立重建 sorted vertex index 和 METIS LCM 整数编码，检查原始 source units 的精确收益、保存的 CHILS one-based IDs 或其他 solver partition flags、binary/input SHA 和固定参数。CHILS/CHILS-ILS 使用经过源码核对的 signed64 total 契约，其余保守 signed32 total；不能无损编码时保留 unsupported/null，不能当作零质量或求解器失败最优性。原生内部 nominal target 与 30 秒 outer hard guard 是不同边界。

性能 kernel 为固定 branch policy、共同 Degree target/restriction、24 顶点 patch、destroy 4、512 patch、每 patch 128 search node 和全局 65,536 search node。它与 authoring TRAIN 配置不同，不能混用其数值。cold nominal T 包含共同 Degree 初始化及 repair；warm 是共同 CHILS(seed1,T/2) 的实际 native 可行 seed、Degree 可行扩展及 T/2 repair。共同 native initializer 在实际实验中复用一次，而每个独立 warm pipeline 的成本必须加上同一份完整 initializer 实测 wall 和 wrapper-self-plus-child CPU，再加自己 repair 的 wrapper 成本。共享执行总成本与各独立 pipeline 成本之和不同；同 nominal T 不等于严格匹配的端到端 hard wall。

## 核心已覆盖的数学与 frame 检查

审核器只导入独立审核 helper，不导入生产 scheduler/oracle/solver。两遍流式归档读取保留一张已解码图及一个 context journal；graph 暂存于工作区 `.research`，不会将全部大图解码驻留。archive root、路径 traversal、绝对路径、反斜杠、非文件/目录项和重复 member 受检查。所有期望请求 key 来自冻结完整 frame；正常行、失败行和显式未返回 stub 都参与 final seen set，不能丢弃失败位置后宣称完整。

局部证明范围包括：原图可行性与 Fraction 精确收益、共同 Degree 初始化前缀、实际 warm starting value、合法 destroy 和外部边界、共同 patch restriction、可行 replacement 下界、真正 clique partition 上界、被声明 restricted exact 的小 patch 的独立精确递推、严格正增益提交、最终 retained incumbent 和逐 patch/全局 node cap、总 patch cap。若 trace 保留了 priority order，还会独立计算 demanded typed feature/rule 的局部排序及 greedy prefix。全图最优性未被宣称。独立 exact recursion 的 ceiling 为 1,000,000 verifier states；达到 ceiling 属于未验证/审核失败，不是实验重试，也不能伪称 restricted optimum 已证。

row 成功条件与 runner 一致：无 runner error、result 存在、completed/feasible 都为 True。程序错误后的保留 incumbent 只进入 diagnostic reward，不进入正常 quality。原图 source scale 被精确除回，graph/load metadata 和 journal/aggregate canonical row 对齐受到核对。terminal marker 存在时要求全 52,548 返回、全 302 contexts、aggregate SHA、status counts 和零 online model/oracle；无 terminal marker 时要求显式 guard 或非零 worker exit，并仍检查完整请求位置。CLI 在审核 assertion errors 非零时非零退出。

## 初版 probes 与已确认关闭的缺口

下列 probe 在 `136b3b…2044` 上执行，全部仅调用独立审核函数，不运行生产算法；原观察保留，不被新版修复覆盖。

| 初版接受行为 | 影响 | `26ee941b…dab6` 复核 |
|---|---|---|
| 将两结点正常 Degree 结果改成一个 `available=False`、`program=None` 的缺失 quality 身份，priority=`program`，没有 patch。`GraphAudit.kernel` 返回 errors=[]，顶层也无 available 结果 guard。 | 缺失身份可在机械检查中被当作正常 fallback，违反 null/no-replacement 契约。 | kernel 和顶层同时强制有 result 的 frozen identity 必须 available=True；新增负例通过。当前实际全部身份 available 的事实单独保留。 |
| 合法模拟 CHILS 收据使用错误 graph/solution 路径，或 wrapper self CPU=-2、child CPU=3；旧 native 检查不拒绝，CPU 合计 1 仍非负。 | 固定参数不能替代 input/output 临时路径契约；正 child CPU 可掩盖非法单相成本。 | native 独立检查 wrapper wall/self CPU/seconds、child CPU 和 overshoot；input.graph/solution.txt 为同一绝对目录，目录有固定临时前缀；正/负例通过。 |
| row 同时给 `target=0.1` 和 `nominal_wall_target_seconds=9`，旧 `key()` 使用前者。 | 请求 membership 可与声明的执行 target 冲突。 | 优先 nominal，并拒绝冲突的 compact target；新增负例通过。 |

## `26ee941b…dab6` 版仍需补强或限定的边界

以下为 `26ee941b…dab6` 当时的静态结论，后续修复见末尾补记；没有用真实归档验证，也没有推断这些情况实际发生。

1. **P2：aggregate 的合法末行截断未和 journal 使用同一错误处理契约。** 第 282–298 行第一遍对 `results.jsonl` 和 `unreturned_assignments.jsonl` 直接 `json.loads`。第 319–322 行只有 context journal 允许在 guard/非零 exit 后存在最后一个截断 JSON 行。真实 guard 可以打断 aggregate 的逐行写入，合法保留 archive 因此会在第一遍抛错，尚未进入 journal/stub 完整性恢复。这是 fail-closed 的假阴性/可恢复性问题，不是错误成功报告。应在知道执行收据后，仅允许已声明中断的最后截断行，保留其 bytes/SHA、明确无完整 receipt 的请求，任何中间损坏仍拒绝；不得补造性能或重跑实验。完整批次必须继续拒绝截断。构造测试目前未覆盖两遍 archive/parser/guard/stub 全链路。

2. **P1：warm initializer 的可用条件比冻结 runner 浅。** 第 356 行只将 common initializer 的 result 放入 `inits[target]`，没有保存该 row 的 runner_error/success。第 366–388 行 warm 前置条件只检查 result completed/feasible；有 result 的 warm 分支甚至直接取 init。冻结 runner 明确要求 `initial_error is None` 加 completed/feasible 才能调用 repair，否则 `NativeInitializerUnavailable`。一个夹带 runner_error 的 completed/feasible common result 可以与 warm 成功行自洽，却未触发现有可用条件断言。应保存完整 initializer availability/receipt，成功 warm 强制原 common row 无 error 且成功；Unavailable 行也应核对所带 native_initial_result 和 receipt SHA 为同一个 common phase。正常 native 无法构造这种合法 source 输出，本条是独立审核契约缺口，不指控生产流程。

3. **P2：policy 单相负时间仍能被正 initializer 时间掩盖。** 第 364–390 行检查总 standalone wall/CPU 非负，并核对加法，未分别要求 `policy_wrapper_wall_seconds` 和 `policy_wrapper_cpu_seconds` 为有限非负。例如 native wall=3、policy wall=-1、保存 pipeline wall=2，当前对应加法及总非负都成立；这仅是静态算术反例，没有调用完整 audit。应分别检查所有实测阶段字段，再保留 warm 加法；异常 repair 也有已执行的 wrapper 成本，应照原 receipt 保留。Native initializer 未可用且 repair 未执行时，不制造 policy 时间或 zero measurement；共同 phase 的真实成本可单独报告。不得由这次补强将 nominal T 改为未注册的端到端 hard deadline。

4. **P2：aggregate-only worker failure 与 unreturned stub 的额外字段验证较浅。** 第 412–431 行检查 expected key、null result/quality、success/returned flag 和完整数量，但没有同正常行一样逐项验证冻结 context metadata、policy role/program/source identity，或拒绝夹带 diagnostic reward、实际 timing/work 等测量字段。compact 重建 context/cohort 且将测量置 null，避免污染质量；其若干 role 字段仍原样复制而未逐项核对。建议对每个 track 的 expected row template 进行只读比较，验证 error 类型/来源与未执行字段的明确 null；不要把未执行测量补成 0。当前应称为完整请求位置和 compact-null 保护，不称为所有原 stub 字段均独立审核。

5. **P2：附加执行/成本收据并非全部深层交叉绑定。** 固定本地 protocol/source zip/deployment/input freeze/root release SHA，加上归档内 selection/audit/protocol/deployment/input bytes 的核对，已提供强身份绑定。但归档 host/execution 的 source_zip 字段、completion 的 protocol/deployment 字段、launch assigned/whole-batch guard、context_loading 的 id/graph SHA/有限非负成本和 context_execution 的 requests/shared cost 没有全部逐项重建。graph bytes、正常 row metadata 和结果 frame 的核心核对不受此观察否定。若这些附加字段用于成本或执行来源表述，应补交叉核验；父进程 self CPU 仍不能解释为全部 worker/child CPU。

6. **证明范围必须保持具体。** 当前检查保留的局部解、上下界、commit 和可重建排序，未重放全部搜索树、pivot、bound-cut 路径或 feature/repair 每个底层调用；meter primitive 和时间是原始执行收据，不能据此声称成本重新计量。trace 中 priority/greedy 可合法为空（例如上界直接 prune），不能一律要求非空；若 greedy `order` 存在，未识别值当前会落入 degree 分支，应拒绝未知枚举。stop reason/budget-exhaustion 的部分字段用于保存/计数，没有完整独立重建其逻辑条件。性能报告只记录本审核器 SHA，宜同时记录三项 helper SHA，精确声明证明版本。`errors=0` 表示审核断言无错，不表示所有算法请求成功。

7. **早期异常未形成统一失败报告。** 缺文件、损坏 JSON、未知 key、异常原生 command 结构和 `VerificationLimit` 都可能在最终 report 写入前抛错；compact rows 可能已部分落盘。它们 fail-closed，但不能把没有报告、非零退出或半份 compact 当成审核成功。可追加不覆盖原文件的失败收据，记录 archive/source SHA、异常阶段和未验证范围；禁止以审核重试为由重新运行科研实验。现有禁止覆盖 audit/compact 的行为应保留。

## Held-out 最新加强的只读复审补记

原 `docs/V06_HELDOUT_VERIFIER_REVIEW_002.md` 保持字节不变，SHA 为 `aca6d9b9af32e6706674cf7971e40dd3a770e854303d01c302fdc2dd363235f0`。本文补记 root 对该文问题的后续修复，不改写旧观察。

本次 held-out 审核器为 `2e6625390671b515dada316da82be0f05af73ff1e3402a50e836fd0c34f39bd9`，测试为 `578d8a5d830acc1a945d1cd07b0e0e250279b7a94df80d08e2c81ddc20fc59ed`，独立执行 13/13 构造测试通过。

三个原已复现缺口均已关闭：总 patches cap 现在直接限制 `patches_attempted <= max_patches`；pairing 拒绝重复端点及左右动作/cluster 不一致；contradictory quotient 必须有显式 witness，每个 witness 的 kind、实际 certified requirement 和循环 equality join 均核验。新增相应负例通过。witness 目前证明至少存在合法 obstruction 和每个保存 witness 有效，仍不是独立枚举所有 SCC/所有 cycle witness 的覆盖证书。

原文其余完整性问题也出现实质补强：按冻结 queue 固定原 registration/root release；分别按 R2 protocol SHA 与 EoH freeze SHA 核验 execution registration/source/selection/control/certificate/workers/frame；worker failure 拒绝伪造 interface/paired/kernel summary；missing 身份核验全部 72 唯一 state/family/cluster/split、精确 coverage/null timing；重建 quota shortfalls、normal budget-stop/status coverage、terminal missing/worker/interface/kernel counts 和全 original/five-relabel robustness mean/worst/null summary。以上来自静态代码阅读和纯 summary 构造测试，未调用真实归档 `audit()`。

仍需沿用原文范围限制：prior TEST certificate proof 被当作既有独立审核及其 bytes 的信任链，不由本次重新运行 oracle；family macro 的全部 verified error incumbent 仍是诊断，不能据其非空 summary 声称正常性能全部成功；实际工作/时间未重新计量；早期异常/ceiling 必须记为审核未完成。新 13 个测试不覆盖完整归档、release 深层数据或全部 null/worker 组合，不能替代最终完整批次审核。

本审查只提交审核器代码层面的独立结论。完成实验后，应以当时的固定 verifier/helper SHA、原始 archive SHA、实际完整请求计数和明确成功/失败/null 统计追加正式审核报告，再决定哪些证据可写入论文。

## 补记：root 第二次边界修复的独立复核

再次阅读的性能审核器 SHA 为 `e220fccf126877e142f155c021488a494887b27bca605efd84c94de3ad1a3a36`；性能测试仍为 `849a48dc8de44f39cf9c9285cbe3feefa868f3b182acb97fb62b146286090d8d`，held-out 源码/测试 SHA 不变。重新执行同样 14+13 个构造测试，27/27 通过（0.004 秒）。执行前后源版本一致。新增的顶层归档分支没有新增端到端构造测试，因此本段对这些修复的确认是静态复核，不是实际存档已通过或全链路负例全部覆盖。

| 前段问题 | `e220fccf…a3a36` 的实际变化与状态 |
|---|---|
| aggregate 末尾截断 | 第一遍现在保留坏尾行的 hash，只允许成员末尾无后续 bytes，并延迟要求原 execution 为 guard/非零 exit；有 completion 时明确拒绝 partial aggregate。中间损坏仍抛错。这个合法 aggregate-tail 处理缺口关闭。`unreturned_assignments.jsonl` 仍严格要求完整 JSON，这些 stub 是 parent 在 worker 结束后生成，不能把缺失 stub 当成完备请求收据。 |
| warm initializer 成功前提 | 新增 `init_rows`；有 result 的 warm 行要求原 initializer row successful=True、runner_error=None，且原 result completed/feasible 为 True。原 successful warm 接受缺口关闭；失败分支的对称性见下段限制。 |
| 正 initializer 掩盖负 policy 时间 | policy wall 非 None 时独立检查该 wall 和 CPU 为有限非负，包括 repair exception 行。原负 policy 算术反例关闭；已执行 cold phase 的 null 时间边界见下段。 |
| stub 字段浅校验 | 新增 frozen context metadata 和所有 policy role/program/source/run/origin 比较，并拒绝原 reward、诊断 reward、fraction、standalone/policy wall/CPU。核心身份和收益污染缺口关闭。未保存测量仍在 compact 中明确 null；并未证明任意额外未经使用字段的真伪。 |
| host/launch/terminal 深绑定 | 新增 host/server/deployment source zip、launch 全 frame、root release、14,400 秒 guard 的交叉绑定；terminal 绑定实际 protocol/deployment、exit=0、无 guard/partial aggregate。上述字段的原缺口关闭。context loading/execution 的额外成本收据范围仍需独立限定。 |

另核对 compact 的科学分组：`source_cluster` 来自冻结 context 的 source_cluster/cluster/pair_id；fresh regime/profile 可由冻结 source 嵌套字段取出。这个改变是从原 metadata 推导分析字段，没有修改原数据或重新分组挑选结果；C3 exploratory 身份仍保留。

剩余可限定的小边界如下，均未用真实结果复现：已执行 policy phase 的 wall 为 None 时会跳过单相断言，cold result 分支也没有强制其非空，宜强制实际已执行 phase 的 wall/CPU 均为有限非负。`NativeInitializerUnavailable` 行仍只核对 init missing/completed/feasible，没有使用其原 row error，亦未核对携带的 `native_initial_result` 和 canonical receipt 与共同 phase 完全一致。对于失败 initializer，不能伪造额外 native receipt 或复用不同 seed；应保存真实诊断而不产生正常 warm 测量。context_loading/context_execution 的有限非负成本和身份、helper SHA、完整 stop-reason/工作路径证明，以及统一异常失败收据仍按前段范围限制处理。它们不要求重新运行冻结实验。

## 补记：纯 phase 收据检查与完整审核源标识

独立复审 `e6c3d41e8f9159751dc77e17954af9a2a39679eee0032d471b36071c212697d1` 及性能测试 `78eb71ad81c83b1604010cd8f4ca121c2452021e6ca89de4692c807f970f3a5c`。新增 `successful_initializer` 同时要求原 row 无 runner_error、successful=True 和 result completed/feasible 为 True；`policy_phase_receipts` 用此条件判断 warm 是否真正执行。每个已执行 phase（包括 throw）必须保存两种有限非负 wrapper 时间，未执行 phase 两种时间都为 null；phase nominal target 仍严格按 cold T/warm T/2。返回 result 必须来自已执行 phase。Unavailable 行必须真正是 available 策略的失败共同初始化，保存同一个原 native_initial_result 和 canonical receipt，并明确无 result/advanced track。原 e220 补记的两处残余边界因此关闭。

独立执行新增的 17 个性能构造测试及 15 个分析构造测试，32/32 通过（0.118 秒），其中新增性能负例覆盖缺失任一 phase 时间、负 CPU、带 runner_error 的 completed/feasible 初始化仍正确阻止 repair、篡改失败 native receipt，以及成功初始化不能伪称不可用。没有运行顶层真实 archive audit。

root 随后只增加 report metadata，最新审核器 SHA 为 `59f5b29283302cfc468acdc37318e583af7bea01ac8658c609c29f73b0b51d9a`。本次只读确认新增 version=`v06_independent_performance_TEST_audit_001`，并记录原三个 helper 的 `independent_helper_sha256`，原 `audit_source_sha256` 保留。冻结科研 runtime/数据未改。此元数据补强让后续分析可以拒绝旧/不完整审核来源，不能把已记 SHA 本身解释为重新计时、重放全部搜索路径或实际正式结果通过。

保留的范围限制为：完整结果尚未由本次审核读取；证明只覆盖保留 trace 的明确部分，额外 context load/execution 成本仍是原收据；失败初始化的 warm compact 可能没有单独 pipeline 成本，真实失败成本在 common_initializer track，分析必须明确成本条件；早期异常/ceiling 仍需 fail-closed。原初版观察和各次修复记录均保留。
