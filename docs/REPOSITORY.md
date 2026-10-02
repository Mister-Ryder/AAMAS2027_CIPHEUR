# 第二篇代码仓库

GitHub：`https://github.com/Mister-Ryder/AAMAS2027_CIPHEUR`

仓库用于 AAMAS 2027 第二篇的持续开发，首版为 CIP-Heur 可运行研究底座。当前为公开仓库。

## 已纳入版本管理

- `cipheur/`：方法实现与 LLM 接口。
- `configs/`、`examples/`、`tests/`：配置、示例和完整性检查。
- `docs/`、`paper/`、`manifest/`：论文细读、方法合同、摘要目标和来源记录。
- `baselines/foundation_v0.1.0/`：首版已冻结的两套运行记录，包括提示、候选、证据、源码快照和收据。记录保持原始字节；不修改既有收据。
- `.github/workflows/integrity.yml`：Python 3.10/3.13 自动运行完整性检查和离线示例。

临时 `.research/`、日常 `output/`、缓存、密钥文件和本地 ZIP 不进入 Git。旧 ESWA 项目与 C3 不复制到新仓库；适配器通过配置引用原稳定底座。

## 开发与冻结

`main` 为当前可运行版本。较大改动建议在功能分支完成，再合入 main。首版标签为 `foundation-v0.1.0`，用于准确恢复本次底座；后续实验冻结新的版本标签，保留原始运行记录，不覆盖历史结果。

本地提交后推送 `main` 即同步到 GitHub；常规 Git 连接本身不会监控文件变化或自动提交。

## 自动检查范围

本机的 39 项检查全部通过；没有原稳定项目或 NumPy 的 GitHub runner 会明确跳过 3 项 V51 集成检查，其余 36 项可直接运行。这不等于在云端验证了 V51 全数据或论文有效性。

自动检查只使用人工开发示例和回放候选，不提供 API 密钥，不发起模型调用，不进行正式效果实验。
