# SNSD-v5.1 原始底座复用合同

本项目通过 `cipheur.v51_adapter.load_v51_pair` 只读调用冻结项目中的 `data.py`、`graph.py`、`verifier.py`。旧项目始终决定 C3 数据解析和冲突边的含义；不复制原算法、不改动旧目录、不向旧目录写入 Python 缓存。适配层只需要可选依赖 NumPy；独立 synthetic smoke 不需要原项目或 NumPy。

```python
from pathlib import Path
from cipheur.v51_adapter import load_v51_pair, verify_v51_selection

left, right = load_v51_pair(
    Path(r"E:\01-Joycecyq\2026-ESWA\DAI2026_SNSD_V51_STABLE"),
    limit=64,
    parameter="ground_trans_time",
    before=340,
    after=500,
)
print(len(left.contacts), len(left.edges), len(right.edges))
print(verify_v51_selection(left, ["0"]))
```

`stable_root` 指向稳定包根目录；`csv_path` 可指定其他符合旧加载器合同的 CSV，未指定时读取 `SNSD_V51_FINAL/data/C3.csv`。模型参数只允许 `ground_trans_time`、`satellite_change_time`、`satellite_trans_time`；非目标参数固定为旧默认值 340、150、300。两个图的 contacts 顺序、原 ID、资源名、权重、建链时间完全一致，只改一个约束参数并重新运行旧建图函数。

原 ID 转为字符串。权重仍为建链时长；跟踪起止时间、原资源整数 ID、priority 保存在 `provenance.arc_metadata`。完整 CSV 和三个导入源文件各自记录绝对路径与 SHA-256；每个上下文还记录原图哈希、总机会数、前缀规模、约束参数与干预增删边数。

默认 `limit=64` 只使用 CSV 原始顺序的前 64 个机会，并显式标为 `scope='prefix_subset_smoke_only'`。这种前缀不构成代表性样本，也不证明完整 C3 性能或真实数据偏好反转。当前 C3 前 32 个点在 ground gap 340/500 下均有 1 条边，前 64 个点均有 24 条边；默认干预未改变这些小前缀的图。是否改变边以运行的 `provenance.intervention_edge_changes` 为准。

必须保留旧同卫星部分交叉区间规则：若后一机会从前一机会内部开始，但在其后结束，只有交叉长度小于 `satellite_change_time` 才冲突。不能用普通区间重叠规则替换。该规则的适配测试另用四条人工机会验证，独立于 C3 的有效性证据。

`verify_v51_selection` 使用原只读检查器，保留重复 IDs 与越界映射，不自动修复选择。它同时输出 contact IDs 和 mapped local integer IDs。此函数需要 `load_v51_pair` 直接返回的图对象；通过 `Graph.to_dict/from_dict` 重建后，普通 `Graph.feasible` 仍可用，如需原检查器需重新加载适配图。

从本项目根目录运行完整性测试：

```powershell
python -B -m unittest discover -s tests -p test_v51_adapter.py -v
```

默认在同级 `2026-ESWA` 目录寻找稳定包；迁移后可设置环境变量 `CIPHEUR_V51_STABLE_ROOT`。原包或 NumPy 不存在时，旧包集成测试会跳过，参数校验测试仍运行；实际调用适配器会明确报错并提示使用独立 synthetic smoke。以上均是适配与合同测试，没有运行有效性或性能实验。
