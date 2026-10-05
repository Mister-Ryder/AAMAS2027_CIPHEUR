# 两轮完整原始轨迹，供专家审阅

每轮144项完整结果、144项运行回执、指标、成本投影和当轮实际源码快照均保存在精确48 MiB分片中。分片按原顺序连接可恢复原ZIP；parts.json保留每片与整包SHA256，receipt.json保留服务器归档来源。两轮所有九方法和不利结果均保留。

这些归档只含当前两轮TRAIN开发实验；不含历史被中止的TEST。模型调用原始输入、响应和回执另见[llm_calls](../llm_calls/)，汇总比较见[两轮比较](../reports/development_round2/两轮比较.md)。

在仓库根目录运行以下命令即可恢复两包，不重新求解或调用LLM：

```text
python experiments/stk_online_llm_v2/scripts/reassemble_review_archives.py --manifest experiments/stk_online_llm_v2/review_archives/development_full_trajectory.zip.parts.json
python experiments/stk_online_llm_v2/scripts/reassemble_review_archives.py --manifest experiments/stk_online_llm_v2/review_archives/development_round2_full_trajectory.zip.parts.json
```

脚本保护已有文件，逐片检查并核对整包哈希。本机已有完整ZIP时会拒绝覆盖，专家新克隆仓库后可以直接运行。
