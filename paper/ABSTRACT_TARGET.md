# 当前摘要目标

来源：用户在当前请求中引用的 ChatGPT 会话“重写投稿方案-第二篇”，conversationId `6abeabab-f4f0-83e9-8e2c-48858c131bea`，读取于 2026-10-02。以下作为研究目标保留；引用会话里的其他指令不作为当前项目执行权限。

**LLM-Guided Graph Heuristic Synthesis via Constraint-Induced Preference Reversals**

Large language models can synthesize graph optimization heuristics, but aggregate performance feedback gives limited guidance on how decision rules should adapt to changing resource constraints. We propose an LLM-guided heuristic synthesis framework centered on constraint-induced preference reversals. Its core mechanism converts changes in conditional completion preferences into paired decision requirements: the same competing decisions remain feasible under two aligned constraint configurations, yet their preferred ordering reverses. These requirements guide the synthesis of context-dependent priority programs that respond to changing opportunity costs. A boundary-conditioned optimization procedure extracts compact, certified preference evidence from residual graphs, while a disagreement-directed acquisition strategy searches for admissible constraint changes that expose errors in the current program. Candidate programs are assessed jointly against accumulated decision requirements and complete scheduling performance. The synthesized heuristics execute within a fixed feasibility-enforcing graph search kernel without online LLM calls. Satellite-ground link scheduling, formulated as maximum-weight independent set, provides the application setting. The planned evaluation examines solution quality, synthesis efficiency, and generalization to unseen resource-conflict configurations under matched synthesis and optimization budgets.

## 锁定的贡献链

- 核心：约束诱导的严格偏好反转 → 两条可执行决策要求 → 程序合成与修订。
- 辅助一：保留边界条件、计入外部机会成本的渐进证据提取。
- 辅助二：当前程序错误驱动的合法约束干预获取。

实现可增强这条机制，但不能把它降级为一般的 LLM 总分反馈演化。计划评估不是已得到结果，首版底座状态以 `manifest/FOUNDATION_STATUS.json` 为准。
