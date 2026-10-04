# V07 核心机制数据的数学判据

本判定基于已完成的输入 profile、48 个 TRAIN 图及 556 次 alias 分类，不重跑数据、不读取 TEST 效果。结论是：**C6/W6 已通过原输入与配置图适配，仍只是核心机制证据候选；严格偏好、真实同标签再现及 V07 kernel 收益尚未建立。** 结构规模或可区分性不能补足这些缺口。

## 1. 同一个可执行问题、同一对竞争动作

固定机会集合、原 duration 权重、资源谓词与配置 \(\gamma\)。令状态 \(s=(U,F,X)\) 明确可选域、承诺和排除；动作 \(a,b\) 必须在同一状态可行。本文“同竞争动作”的原固定接触契约进一步要求 \(\{a,b\}\in E_\gamma\)，即二者不能同时纳入。更一般接口须另外定义竞争，不能把所有相同特征节点都算作决策冲突。

定义同边界的强制纳入最优值及差值：

\[
M_{\gamma,s}(a)=\max_{I\in\mathcal I(G_\gamma[U\cup F]),\ F\cup\{a\}\subseteq I,\ I\cap X=\varnothing}\sum_{v\in I}w_v,
\qquad \Delta_{\gamma,s}(a,b)=M_{\gamma,s}(a)-M_{\gamma,s}(b).
\]

若可证明 \(M(a)\in[L_a,U_a]\)、\(M(b)\in[L_b,U_b]\)，则 \(\Delta\in[L_a-U_b,U_a-L_b]\)。下界严格大于预定 \(\epsilon\) 才标 \(a\succ b\)，上界严格小于 \(-\epsilon\) 才标反向；区间跨零是 **unknown**，不是 tie。Tie 需要精确零区间或边界保持的对称双射证明。配置反转须相同机会/动作、两侧共同可行且竞争、各自相同声明边界，并有 \(\Delta_{\gamma_0}>\epsilon\) 与 \(\Delta_{\gamma_1}<-\epsilon\) 的证书。

## 2. 精确信息缺失与规则拟合分开

完整表示 \(\phi_{\gamma,s}(v)\) 使用全部声明字段及确切算术。发生项 \((\gamma,s,v)\sim(\gamma',s',v')\) 当且仅当完整向量**精确相等**。把已证实的严格要求映射到这些等价类，得到有向 demanded quotient \(Q\)。

**有限要求的判据：** 存在任意标量函数 \(f(\phi)\) 满足全部严格要求，当且仅当 \(Q\) 无有向环。环将导出 \(f(z)>f(z)\)；无环时按拓扑顺序赋分即可。特别地，同状态 \(\phi(a)=\phi(b)\) 且已证 \(\Delta(a,b)\ne0\)，产生自环，才是一个精确信息障碍。只有 equality census 时尚无 demanded quotient；仅缺少 alias 或全部标签为 unknown 时，不能宣称信息门证明了修复。

无环不保证有限 typed rule grammar 能实现拓扑排序；这是表达能力/系数拟合问题。结构特征分开两个根也不保证标量方向正确或全局 \(Q\) 已无环。当前 base9 含显式 gap，340/680 时所有完整向量都会因该坐标而改变：**配置反转本身不证明跨配置表示冲突**，必须检查实际精确 equality joins 和严格要求。

## 3. 结构再现不能代替偏好再现

反例：单位权重、单位 duration 的六顶点路径 \(P_6\)，比较相邻顶点2和3。它们 degree、邻居权重和/最大、compatible-weight 等完整 base9 字段相同，非 twins，第二轮加权 WL 可以区分；但最大独立集大小为3，\(\{2,4,6\}\) 与 \(\{1,3,5\}\) 分别包含二者，所以 \(\Delta(2,3)=0\)。因此“non-twin/WL 可分 ⇒ 严格偏好”是错误推理。

TRAIN 定义的 identifier-invariant 结构签名在未来再次出现，只能证明输入模式覆盖。若两个**完整加权、配置和边界**问题存在把 \(a,b\) 对应过去的同构，等权可行解双射才保证同一 \(\Delta\)；局部 motif 或资源身份相同通常不够。真实同标签再现需独立取得相同任务/边界下的 sound 标签，并按预定结构类和全部分母统计；目前未计算。

## 4. 学习优先级必须进入真实 kernel 路径

记 \(T^r(s;B)\) 为共同 kernel 在预算 \(B\) 下使用排序头 \(r\) 的执行路径，\(Y^r(s;B)\) 为可行 incumbent 值。表示/规则改进要作用到质量，至少须被实际调用并改变有因果相关性的选择路径；即使 \(T^{r_1}\ne T^{r_0}\)，也不推出 \(Y^{r_1}>Y^{r_0}\)。严格纳入最优值标签也不自动证明 B&B pivot 更省工作，因为 pivot 会探索两分支。

证书若对应 full residual，而实际评分域是 outside-fixed patch，必须重新对齐 \(U,F,X\) 及特征活动域。对固定边界/固定区域的已完成 exact patch，其最优**值**与排序无关；不同等值 witness 仍可能影响后续轨迹，不能据此证明所有全局路径恒同。原 V06 TRAIN 已观察到排序/pivot 改变、全部受限 patch exact、候选最终 reward 平局；这说明该运行机制的质量通道没有区别，不是证明大数据会修复它。成本改善也需要实际计费后的工作/时间证据。

## 5. 当前层级判定

|层级|已证实|尚未知或不满足|
|---|---|---|
|输入与原任务|C/W：三天、nested 系列、原 duration 秒；C6/W6 的机会键交集为0|不能将档位作独立 TRAIN/TEST；行不重叠不证明统计独立或观测来源|
|配置反事实|48/48 TRAIN 图完成；同窗口原机会和权重保留，340→680 全部改变图|原 V51 crossing-overlap 谓词仍是原任务，不能偷换理想区间模型|
|精确表示碰撞|556 个两节点 full-base9 classes；1,112/282,066 action occurrences|碰撞稀少不等于适合或不适合，严格 demand 仍缺|
|真实竞争库存|47 个 adjacent alias occurrences：43 non-twin、4 true-twin；531 跨配置 pair 中46在两侧竞争|另509 occurrences非相邻；对应485 unique pairs两侧均非竞争，记 `notqueried_noncompeting`，不是 oracle unknown|
|对称与更强结构|4个 true-twin 空边界 \(\Delta=0\) 已证明；550个 occurrence被WL2区分|552 non-twin不是552严格冲突；WL区分不是标签，也不是现有typed库可实现证明|
|严格偏好/反转|可预声明46竞争 pair、92个配置端点差值比较|尚无这些比较的严格证书；不得把556作为primary decision-conflict分母|
|再现与部署|重复资源/粗结构、合法输入候选已知|真实同标签再现未计算；V07实际边界/排序敏感性与收益未知|
|公开替代场景|WDP/UAI原图适合secondary solver兼容/质量；SatNet实际五周请求可读且跨周不重叠|generic图缺物理配置生成映射；SatNet含可变/拆分轨长、多天线及维护，当前不能无损直接MWIS化；CelesTrak是派生仿真的轨道源|

## 6. 原 duration 下的下一步决策

1. 在冻结的46个竞争 pair 框架中保留全部92端点比较、4个已证对称tie和非竞争排除分母；不用WL可分、预计有利方向或未来效果筛选。Sound 区间可用可行下界、有效上界和合法条件组件抵消，预算耗尽必须 abstain。初始图连通不证明条件 residual 必定难，但也不能预设它会分解得足够小。
2. 如果多数证书 unknown，先报告“给定成本下证据覆盖不足”。可预声明统一预算扩展，或转向应用真实产生且与部署一致的局部边界；后者是新的 scope，不能继承 full-residual 标签。不得删掉难例后把剩余成功比例当总体适用性。
3. 若 sound closure 后严格冲突/反转仍稀少或全tie，保留该自然场景边界：它可继续作为输入/求解器或成本研究，但不足以承担“普遍信息修复/质量优势”的核心证据。若已有严格 demanded obstruction，则再检查joint representation-rule能否满足要求、实际 kernel 路径与共同计费收益。两个步骤都不能由更大的 \(n\) 推出。保持原 weights、times、edges 生成语义；新的业务任务构造只能来自独立场景依据，不能为了制造alias或优势调权。

依据：[C系列输入](V07_C_SERIES_DATA_ASSESSMENT.md)、[W系列输入](V07_W_SERIES_DATA_ASSESSMENT.md)、[48图screen](V07_CONTACT_SCENE_SCREEN_002.md)、[556分类](V07_SCENE_ALIAS_MATHEMATICAL_CLASSIFICATION_003.md)、[TRAIN路径诊断](V07_TRAIN_CONTRIBUTION_CHAIN_DIAGNOSIS.md)、[公开图实际审查](V07_PUBLIC_BENCHMARK_SCENARIO_AUDIT.md)、[SatNet实际输入](V07_SATNET_INPUT_FEASIBILITY.md)。竞争计数直接读取既有003 summary，SHA256 `4b71e538fbdaa1a8c4fb8e32035403c30bba4f7f14a7c0e635e846114c4104d7`；没有新计算图或偏好标签。
