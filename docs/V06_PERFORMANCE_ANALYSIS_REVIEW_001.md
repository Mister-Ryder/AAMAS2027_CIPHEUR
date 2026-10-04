# V06 性能分析脚本：独立源码与构造输入审查 001

审查日期：2026-10-04。初版分析源码 `scripts/analyze_performance_test_v06.py` 的 SHA 为 `bea826423d8c6a3abcee44179772b2d6a09cc9186b27cafba19dd715db4cc5a2`，测试 `tests/test_analyze_performance_test_v06.py` 为 `b62d803aec3c850277ec209dc0c1da7453fe60e8dff8cfce46ccfa797dc96e8e`。本段记录修复前观察，后续修复追加而不覆盖。没有读取任何真实 TEST compact/归档/指标；只阅读代码、两个冻结分析 config 和运行纯构造测试，没有调用 optimizer/runtime/oracle/LLM。

## 核心科学组织

15 个初版分析构造测试独立全部通过（与 17 个性能测试一起为 32/32，0.118 秒）。源码不访问 AST 或原始 archive。其严格入口要求 302 contexts、23 frozen 策略身份、52,548 assignments 和每个 target/seed/track 完整矩阵；分析只能从零错独立 audit 所绑定的 compact bytes 开始。

同 context 内先平均三个 native seeds 或四个角色成员，再跨 context/source cluster 聚合；重复 AST 身份保留，不能择最好方法/seed/作者位置。完整角色/seed group 只要一个 reward null，complete mean 就是 null，同时另存 available mean、requested/returned/success counts 和 status/error reasons。没有将失败、unsupported、unreturned 的奖励设为 0，所有三档 target 的 null 点继续存在。纯构造例：native seed rewards 10/null/30 的 complete mean 为 null、available mean=20，成功 2/请求 3；quality 成功字段夹带 error 或非空失败 reward 会被拒绝。

固定质量参考为原 CHILS seed1，不是三 seed 平均或 saved best。共同 track Degree、W/R/O 角色均值与四个原 authoring block 的单独对照区分；EoH 只作单独 quality baseline，没有伪造同 authoring block 的因果对照。缺 reference/零 reference 的比例增益为 null，负增益保持负数。joint W 与非 guarded quality comparator 的差异包含 selector 与框架作用，不能解释成单一 witness 或 LLM 因果效应。

fresh 左右端点共享原 pair cluster；其他公共/C3 保持 source cluster。2000 次固定 seed=261004 的 cluster bootstrap 对同 assigned clusters 使用同抽样，保留 null cluster，仅在 draw 有定义值时计算统计量，报告 assigned/defined contexts/clusters/replicates。四个 authoring draws 不因 source intervals 变成独立 model-population 实验。NumPy 与标准库使用同 Python-Random draws；构造测试验证两者相同结果。CI 是浮点统计区间，精确 Fraction 用于原目标、平均和差，不将 CI 宣称为形式证明。

原始 rewards 按 population/family 保持隔离；仅 dimensionless paired gains 和成本进入跨 family population contrasts。C3 interval 与 legacy 都保持 exploratory 标签。曲线以 nominal T 为注册横轴，actual standalone CPU/wall 为另外的点指标，没有插值假造 anytime trace，也没有承诺严格端到端相同 deadline。

## 初版入口来源缺口

`load_audited_rows` 检查 errors 必须为 int 0、compact SHA、archive SHA 的格式、固定 constants 和 23 个 policy metadata，但没有要求审核 report version、正检查数量及 by-kind 一致性、空 error_details、已审查审核器 SHA 或独立 helper closure。故一个零检查的旧/伪造 report 只要填上原几个字段并绑定内部合法 rows，不能在该入口被拒绝。这个结论来自静态阅读；未读取真实 report，也未假称已证明真实批次失败。

root 已授权仅修复此分析源码及其 tests；冻结科学运行器、结果、配置、分组、selector、bootstrap 方法不改。强来源 guard 必须固定被审查的审核器及 helper SHA，并保存独立 report bytes 的授权 digest；不能仅以 caller 提供的 `errors=0` 当作来源证明。正的元数据检查本身仍不等于密码签名，最终报告 SHA 需来自 root 已冻结、独立审核的存档链。

## 成本和失败统计的必要限定

`number()` 拒绝 bool、字符串、NaN、无穷和负的测量时间/work，允许真正缺失 null。实际非空成本包括失败尝试已执行的 wrapper 工作，不是只统计质量成功。每个 cost field 按该字段的已知成员平均并记录 defined-member counts；跨 context 也按各自已知成本条件平均。它与 complete reward 必须全部成员成功的条件不同，质量/成本两坐标不能笼统说成同一个完整 pipeline 总体；每项 defined/requested 分母需要同行显示。缺失时间不能补成 0，null 不代表无代价。

warm 每个已知 pipeline 保留整份共同 initializer 成本再加自身 repair，不按 23 policies 摊薄；图加载单列，另提供 standalone-plus-load，shared actual batch setup 不能重复解释为独立 pipeline 总 CPU。native child CPU 与 wrapper-self CPU 已由审核 compact 保留，分析不重新测量。

重要上游范围：原 native initializer 已失败且 repair 未执行时，warm compact 的 standalone/native/policy 成本可能都为 null，而 common_initializer track 保存真实失败成本。分析没有足够字段重新分配此失败成本，不能把 warm 已知均值称为所有请求的端到端尝试成本，不能将昂贵失败当作 0。共同 initializer 的失败数和已知成本必须独立显示。这个限制无需重新运行实验；若以后添加 attempted-pipeline-cost 字段，应基于同一原收据明确追加转换与审核，不能生成不存在的 repair 测量。

其他边界：complete/available quality 及 cost 的 bootstrap 都显式条件于定义的 context，不自动修正非随机失败或 transport 条件选择；少量公共 sources 的 CI 只描述这批来源；full matrix 和 codec limits 仍应同时列出。早期 parse/schema/hash 失败会抛错而不生成成功分析；没有 output 或半份 output 不代表零错误。输出目录禁止覆盖，修复或另版分析应使用新目录。

本审查只验证统计代码与构造输入的处理，不是任何真实 TEST 性能结论。

## root 授权修复后的最终版本

分析源码最终 SHA 为 `b01f05e1706d7a8ea10d2629f3c924170855b693f6c621bb80d46a370a5b88d2`；分析测试为 `29133158482c9573d82301ceab18ebf1ff0475d6bfbf2235dc4e797a8a21ee91`。固定接受的独立性能审核器为 `59f5b29283302cfc468acdc37318e583af7bea01ac8658c609c29f73b0b51d9a`，三个 helper SHA 与前述审查相同。原初版观察和 SHA 保留在本文，未覆盖旧结果或更改任何冻结科学 runtime/数据/config。

新增入口要求：root 确认的报告 SHA 必须为完整小写 hex 并与实际 report bytes 相等；report version 必须是当前独立性能审核版本；errors 必须为严格 int 0、error_details 必须为空 list；check 总数须为正 int、by-kind 各 count 为正 int 且和相等，原完整 frame/source/302 lossless graph checks 必须存在；complete 或 interrupted 两种最终 batch disposition 必须恰好一个，complete 还须有成功 exit/terminal counts 检查。原已审核 guarded frame 可继续分析完整请求位置和 null，不被误当成全部成功。

入口同时核对 report 与本地数学审核器的已审查 SHA，以及 report/local 三项 helper closure。随后仍检查 compact SHA、archive digest 格式、固定 constants、全 52,548 matrix 和 frozen 23 policy metadata。缺来源、旧版、零检查、矛盾计数、隐藏错误、helper 被修改、任意替换报告都在读取 compact 指标前拒绝。完整检查元数据不是密码签名；必需的 root-authorized report SHA 应从正式独立审核后的冻结收据取，不能自算一个任意构造报告的 SHA 后把它称为授权。

新增 `cost_scope` 在 top-level analysis、角色/身份 context estimates、summary 和 contrast 输出中明确：时间均值条件于已知成员/contexts，包括有实际成本的失败尝试；与完整质量的全成员成功条件不同；未可用 warm 初始化成本只在共同 initializer track，没有把 null 当 0；已知 warm standalone charge 完整 initializer 加自身 repair；shared execution/load 范围单列。没有改变任何 estimator、role/source 分组、contrast、2000 次 bootstrap 或三档 target。

最后一次必要构造验证实际执行 17 个性能 + 20 个分析测试，**37/37 通过（0.110 秒）**。5 个新分析测试覆盖正确/guarded 元数据、授权报告 hash、旧/缺失/伪来源、空/矛盾/缺 terminal 的检查计数和 local helper drift。所有输入为构造对象，不是正式 audit、实际 TEST 行或新增实验。此后没有重复测试或追加边界 probe。

最终调用方式（从项目目录执行；大写占位替换为 root 冻结后的实际 artifact）：

```powershell
python -B scripts/analyze_performance_test_v06.py --audit "FINAL_AUDIT_JSON" --audit-sha256 "ROOT_FROZEN_AUDIT_SHA256" --rows "AUDITED_ROWS_JSONL" --out "NEW_ANALYSIS_DIR"
```

`--audit-sha256` 为新增必需参数。程序会在报告、源码 closure 或 compact 不匹配时停止；输出目录必须为新路径。函数 API 同步为 `load_audited_rows(audit_path, rows_path, expected_audit_sha256)`。真实完整存档只需进行一次必要正式审核再分析，本文测试不代替该审核。
