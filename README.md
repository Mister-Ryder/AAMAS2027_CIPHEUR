# AAMAS 第二篇：约束适应的表示—规则联合合成 v0.2.0

目标摘要：**LLM-Guided Synthesis of Constraint-Adaptive Heuristics for Satellite–Ground Scheduling**。

当前已实现认证的反转/保持关系、精确表示矛盾检测、typed 图特征组合、规则合成与修复、规范/质量/成本联合选择和冻结部署。已执行初始实验及新实例复测，完成可复现分析 notebook 和官方 AAMAS 2027 模板的论文基础稿。公开仓库：[Mister-Ryder/AAMAS2027_CIPHEUR](https://github.com/Mister-Ryder/AAMAS2027_CIPHEUR)。

## 当前结果与结论范围

初始留出集 36 对、72 个上下文；新实例复测 35 对、70 个上下文。全部参考最优值计算完成，全部 1,136 次方法—上下文调度可行；240 次 C3 调度另通过原 V51 验证器。

| 测试 | 联合程序 / 最优值 | 规则对照 / 最优值 | 联合严格要求 | 规则严格要求 |
|---|---:|---:|---:|---:|
| 初始留出 | 99.7339% | 99.5222% | 67/68 | 45/68 |
| 新实例复测 | 99.6804% | 99.7445% | 61/64 | 41/64 |

当前助手参与提出候选，**自动 LLM API 调用为 0**；定向联合、共享候选自由联合、无规范门控的质量—成本选择、非 LLM 枚举选中了同一程序。实验支持机制已落实，尚不支持 LLM 或定向生成的额外收益，也不支持普遍调度质量优势。复测 C3 中联合程序弱于规则对照。设计探针、随机问题和 C3 局部子问题分别报告，不能代表完整 69,923 条 C3 数据的全局性能。

## 直接运行

核心流程只需 Python 3.10+。旧原始数据的再生成需要 NumPy；归档数据上的合成、部署和完整性验证不需要私有原始包或模型密钥。

```powershell
python -m unittest discover -s tests -q
python scripts/verify_artifacts.py

# 完整联合合成流程：使用已认证的训练证据与验证集，回放默认候选
python -m cipheur synthesize --prepared-run experiments/runs/pilot_v0.2.0_audited --config configs/joint_replay.json --output output/my_joint_run

# 冻结程序部署，运行时没有模型和 oracle 调用
python -m cipheur schedule --graph examples/deployment_graph.json --program output/my_joint_run/selected_program.json --output output/my_schedule.json
```

输出目录必须是新的；已有实验不覆盖。`selected_program.json` 同时保存特征 AST 和规则。`schedule` 自动识别旧规则和新联合程序，也支持 `--fixed`、`--excluded` 边界动作。

## 再生成和实验

```powershell
python -m cipheur.experiments prepare --config configs/research_pilot.json --output output/new_pilot
python scripts/build_candidate_bank.py --request output/new_pilot/training_request.json --output output/new_bank.json
python -m cipheur.experiments evaluate --output output/new_pilot --candidates output/new_bank.json
python -m cipheur.followup --pilot output/new_pilot --output output/new_followup
```

`configs/research_pilot.json` 的 `stable_root` 指向本地原稳定包，跨机器需修改。数据生成不按认证成功或调度效果过滤；源数据缺失明确报告，不能把合成问题替代为真实数据。冻结记录写在查看测试目标值与证书之前。复测使用原冻结程序，并检查与原全部分割的机会/图身份无重叠。

## LLM 参与方式

当前方案采用离线合成、冻结部署：LLM 只提出结构特征与规则，证书检查和实际调度评价决定接受与否。部署程序不读训练标签、动作身份、在线最优解或在线 LLM。

`cipheur.feature_provider` 支持 OpenAI Responses、兼容接口、外部命令和明确标记的回放。模型和密钥环境变量必须显式配置；密钥不写入代码。递归严格 schema 与本地 typed validator 双重检查，错误保留，失败不静默回退。更强或更小模型的选择应由同信息、同预算的独立生成实验决定；当前没有把聊天会话伪装成本地模型服务，也不使用 DeepSeek harness。

接口详见 [联合模型接入](docs/LLM_JOINT_PROVIDER.md)，实验下一阶段见 [实验计划](docs/EXPERIMENT_PLAN.md)。额外云算力本轮没有使用，连接凭据不在项目内。

## 论文和分析

- [论文源码](paper/main.tex)：官方 `aamas.cls`，匿名模式，Submission 1997，保留最终采纳摘要；不编造作者单位与邮箱。
- [已编译基础稿](paper/main.pdf)：6 页，包含方法、命题及证明、实验协议、真实结果和局限。
- [可复现分析 notebook](experiments/analysis/pilot_analysis.ipynb)：已从头执行，保存图表与数据核验。
- [实验分析](docs/EXPERIMENT_FINDINGS.md)、[近邻文献](docs/RELATED_WORK_V02.md)、[DRAGON 细读](docs/DRAGON_REVIEW.md)。

分析依赖可选安装：`python -m pip install -e ".[analysis]"`，然后运行 `python scripts/analyze_research.py`。图表计算和绘图代码可编辑，所有输入来自归档实验。

论文使用本机已有 TeX 编译；内置编辑器此次报环境目录错误。安装完备的 TeX 环境中可在 `paper` 目录执行：

```powershell
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

官方类与样式逐字节保留；没有修改字体、边距或缩小正文。参考文献只使用核验的一手资料；未确认的出版字段保持缺省。

## 归档与版本

| 路径 | 含义 |
|---|---|
| `baselines/foundation_v0.1.0/` | 原底座冻结记录，未修改 |
| `experiments/runs/pilot_v0.2.0/` | 第一次实验记录 |
| `experiments/runs/pilot_v0.2.0_audited/` | 同数据/候选/设置的审计修正再执行，不能当独立测试 |
| `experiments/runs/followup_v0.2.0/` | 新实例的冻结程序复测 |
| `experiments/runs/joint_replay_v0.2.0/` | 完整联合合成入口验证，未访问测试数据 |
| `manifest/RESEARCH_STATUS_V02.json` | 当前研究版本状态 |
| `manifest/CURRENT_SOURCE_SHA256.json` | 当前可运行源码和文档哈希 |

原底座说明见 `docs/archives/README_V01.md`，旧摘要见 `paper/archives/ABSTRACT_V01.md`。旧 smoke 入口 `run_smoke.ps1` 保留作回归检查。完整性 CI 覆盖 Python 3.10/3.13、归档哈希、旧底座、联合合成和冻结部署。
