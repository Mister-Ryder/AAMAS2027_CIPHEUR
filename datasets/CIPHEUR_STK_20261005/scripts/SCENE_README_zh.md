# STK 场景打开与编辑

正式机会库各自保存在 `raw/CP-*/`。`scene/` 是可编辑的 STK 11 场景及其全部附带文件，随目录携带冻结的 `CIPHEUR_EOP_20261004.txt`。该文件包含截至 2026-10-04 发布的数据以及未来预测；未来时段使用预测值，不是观测值。

本机 STK 11 无法直接保存到含中文的路径。为保留用户要求的中文 data 目录，生成与打开均在本任务独有的 ASCII 临时目录中完成，再完整保存回 data。不会修改安装目录、其他任务的场景或全局 EarthData 设置。

人工编辑时在终端运行以下命令（把场景 ID 替换为所需正式库）：

```powershell
& 'C:\Users\JIA\.codex\tools\stk11\.venv\Scripts\python.exe' 'E:\01-Joycecyq\2026-AAMAS\data\两篇论文数据定制化构建\CIPHEUR_STK_20261005\scripts\open_saved_scene.py' CP-AU-r000 --interactive
```

编辑完成后回到终端输入 `SAVE`。新的可编辑版本存入该库的 `scene_revisions/UTC时间/`，原始接触、图及实验结果不会被覆盖。直接回车会关闭本次窗口而不保存。脚本仅创建和关闭自己的 STK 实例。

省略 `--interactive` 只进行隐藏加载并关闭；这不会重新计算所有 Access。正式数据已经在首次生成中验证保存、完整复制和重新加载，不需要为日常分析反复打开场景。

数值数据以 `contacts.csv` 为正式入口：完整接触位于规划 72 小时内，端点是冻结的六位微秒数值，收益等于两个端点之差。`access_raw.csv`、`provider_reports.jsonl` 保留 STK 原始双精度输出；跨界及传播缓冲区中的接触另存 `contacts_boundary.csv`，不会裁短并入正式图。
