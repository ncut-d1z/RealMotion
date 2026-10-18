# RealMotion

研究真实载具的旋转—平移耦合，并区分它们何时能作为无 IMU 单目视觉里程计的先验。

**核心结论：道路车的无滑移条件约束速度；普通四旋翼的推力方向首先约束加速度，而不是唯一确定飞行速度。相机杆臂会改变光心运动；某些已知米制安装几何与转弯还可提供条件尺度。**

资料入口见 [references.md](references.md)，完整推导见 [theory.tex](theory.tex)，实际完成/未完成记录见 [PROGRESS.md](PROGRESS.md)。仓库保留原始 [TODO.md](TODO.md)。

## 范围与文件结构

这不是完整 VO、飞控或车辆动力学产品。默认不把 IMU、转角/轮速、飞控指令、真实尺度当成可用观测；合成真值仅供建模和评估。E06 明确讨论新增已知杆臂/重力方向的条件，不是把这些真值偷偷传给 VO。

| 路径 | 内容 |
|---|---|
| `theory.tex`、`.latexmkrc` | 可独立编译的中文 ctexart，含参考文献；无需预生成图 |
| `references.md` | 论文、厂商手册 URL、核查范围、理论/实验映射 |
| `realmotion/models.py` | SI 单位刚体、轮式和四旋翼力学；相机外参；条件尺度 |
| `realmotion/config.py`、`configs/*.toml` | 严格校验、不可变配置；默认/快速检查配置 |
| `realmotion/experiments.py` | 七组无文件副作用的独立实验 |
| `realmotion/runner.py`、`__main__.py` | 命令行、Agg 绘图、完整性清单与原子发布 |
| `tests/` | 解析解、雅可比、退化、参数、重复/并发、失败隔离、文件策略测试 |
| `scripts/` | 已跟踪文件的源文件白名单检查、LaTeX 最终日志检查 |
| `.github/workflows/ci.yml` | 最小权限 Python/LaTeX 检查 |

## 安装与运行

已验证基线：CPython **3.13.5**，NumPy **2.3.5**，SciPy **1.17.0**，Matplotlib **3.10.8**，pytest **9.0.2**。
直接依赖固定在 requirements 文件；不是所有传递依赖/操作系统的完整锁定环境。命令从仓库根目录执行。

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell 使用：.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m realmotion --config configs/smoke.toml
python -m realmotion --config configs/default.toml
```

只执行部分实验、不绘图或将结果放到外部目录：

```bash
python -m realmotion --config configs/default.toml --experiments car_circle finite_chord --no-plots
python -m realmotion --config configs/default.toml --output-root /tmp/realmotion-output
```

Python 接口：

```python
from realmotion.config import load_config
from realmotion.runner import run

config = load_config("configs/default.toml")
first = run(config, "outputs")
second = run(config, "outputs")  # 不覆盖 first，数值实验保持可复现
print(first, second)
```

每次返回唯一的 `outputs/run-<配置哈希前缀>-<UUID>/`，包含 7 个 NPZ、9 个 PNG 和 `manifest.json`（选择子集或 `--no-plots` 时减少文件）。NPZ 仅含有限数值/布尔数组，不使用 pickle。清单记录已解析配置、源码 SHA-256、Python/主要数值库版本、指标和数组/文件哈希。

```python
import json
import numpy as np
from pathlib import Path

folder = Path("outputs/替换为实际输出目录")
manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
print(manifest["experiments"]["car_circle"]["metrics"])
with np.load(folder / "car_circle.npz", allow_pickle=False) as data:
    print(data["time_s"], data["numeric_2"])  # 后轴 x[m], y[m], yaw[rad]
```

## 七组实验

| 编号/CLI 名称 | 核查内容 | 默认配置的重要条件 |
|---|---|---|
| E01 `car_circle` | 后轴自行车 ODE 对照稳定圆弧解析解，四轮接触残差 | 转角 −15°/0°/+15°，轴距 2.6 m，速度 3 m/s |
| E02 `finite_chord` | 恒曲率/变曲率下弦方向与半偏航；错误初始航向先验 | 时间跨度 0.02/0.04/0.1/0.2/0.4 s；转角变化率 4°/s |
| E03 `skid_steer` | 四固定轮完全无滑移时约束秩，必要接触侧滑、有效轮距偏差 | 半轴距 0.28 m；几何/有效轮距 0.55/0.715 m（非产品标定） |
| E04 `lever_arm` | 任意安装坐标下有限刚体恒等式，忽略杆臂的影响 | 杆臂 (0.8,0.15,0.2) m；右/下/前光学相机轴 |
| E05 `quadrotor` | 悬停、悬停偏航、侧飞、偏航侧飞、固定倾斜、带阻力倾斜 | 1 kg，15° 倾斜，线性阻力 0.2 kg/s；完整刚体状态积分 |
| E06 `scale_observability` | 已知米制前向杆臂+转弯；另已知重力方向+推力模型；退化 | 尺度真值 3.7 仅供合成/评价，悬停主动拒绝 |
| E07 `prior_monte_carlo` | 原始方向、硬先验、软先验、创新门控的 RMSE/偏差 | 每个 0°/2°/5°/10° 失配工况 20000 次，根种子 20261018 |

E05 不是完整空气动力学/电机模型：常值旋翼推力，简化各向同性阻力，未含风、桨叶复杂效应、地面碰撞和飞控闭环。
E07 在**位姿方向观测层**加高斯噪声，没有生成图像、运行特征匹配或证明真实外点模型。

配置中的非零初始侧飞速度是物理反例；不意味着一般 VO 必须这样初始化。静止起步可先倾斜加速、再回正机体而仍保留侧向速度。

## 本地正式运行结果（2026-10-18）

以下来自已执行的 `configs/default.toml`，不是预期值；其他平台最后几位可有浮点差异。

| 检验 | 结果 | 正确解释 |
|---|---:|---|
| E01 圆弧 ODE/解析式最大位置差 | 1.75×10⁻¹⁴ m | 数值实现一致性，不是实车精度 |
| E02 恒曲率半角方向最大 RMSE | 5.51×10⁻¹³° | 正确假设下的几何恒等式 |
| E02 错用初始朝向的最大 RMSE | 3.543° | 瞬时速度不等于有限弦方向 |
| E04 有限外参恒等式最大误差 | 1.78×10⁻¹⁵ m | 独立世界坐标计算交叉验证 |
| E05 忽略阻力的最大横向比加速度残差 | 1.774 m/s² | 理想推力约束受到模型失配破坏 |
| E06 已知重力条件尺度 | 3.7000000000000015 | 额外条件下恢复真值 3.7 |
| E06 同样算法忽略真实阻力 | 5.68098 | 有约束也可能得到严重有偏解 |

E07 的结果尤其不宜只挑有利工况：

| 侧滑失配 | 原始方向 RMSE | 硬先验 | 软先验 | 创新门控 |
|---:|---:|---:|---:|---:|
| 0° | 1.993° | 0.251° | 0.275° | 0.398° |
| 2° | 2.003° | 2.015° | 1.874° | 1.976° |
| 5° | 2.005° | 5.006° | 4.644° | 4.233° |
| 10° | 1.985° | 10.005° | 9.281° | 2.454° |

模型正确时先验很有效；中等失配下门控仍可能接受错误模型并显著恶化估计。不能据此宣称门控总优于原始视觉。

## 可重入保证与限制

不改变工作目录、全局 NumPy 随机种子或现有输出；配置冻结；随机流按实验编号划分，改变执行顺序不改变其样本。每次调用只写自己的暂存目录，验证并写完清单后在同一文件系统内原子重命名。失败只清理自己的暂存目录；进程被强杀可能留下隐藏暂存目录，但不会发布假的完整运行目录。

测试覆盖同进程重复调用、两个进程同时写同一个输出根目录、改变实验顺序、故障注入后的旧结果保留。Matplotlib 使用面向对象 Agg，渲染加锁，不依赖 GUI 或全局 current figure。

“可复现”是相同环境中的数值数组相同，不是 UUID、ZIP 时间元数据或 PNG 文件逐字节相同；不是任意线程异步信号重入安全或断电持久性保证。极端参数、推力越界和尺度无激励会报错，而不是静默输出无效数值。改变为零倾角时 E06 的条件尺度会退化；研究该工况应选择其他实验或直接测试模型拒绝路径。

## LaTeX

需要 XeLaTeX、ctex、Fandol 字体及 latexmk。Ubuntu 的一组安装与编译命令：

```bash
sudo apt-get install texlive-xetex texlive-lang-chinese latexmk
latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error theory.tex
python scripts/check_latex_log.py build/theory.log
```

`.latexmkrc` 将中间文件/PDF 放入 `build/`，明确禁用 shell escape。本地已编译为 12 页；最终日志无错误、缺字、未定义引用、需再次交叉引用或 overfull box。此文档不依赖生成图片，9 张实验图通过 Python 按需生成。

## 禁止产物入库与 CI

`.gitignore` 合并官方 Python/TeX 模板生效规则，额外忽略数据、栅格/矢量插图、PDF、媒体、归档及所有运行目录；包括大小写混写扩展名。配置使用 TOML，运行数据使用忽略目录中的 JSON/NPZ。

**仅靠 gitignore 不够**：`python scripts/check_repository.py` 检查 `git ls-files`，按源码/配置白名单拒绝生成目录、未知类型、二进制、符号链接。因此 `git add -f result.npz` 也会导致 CI 失败。不要用强制添加绕过政策；新增合法源码类型应显式评审并修改检查器。

工作流在 main 推送、PR 和手动触发时检查；仅修改四个根目录 Markdown 说明文件不会启动数值/编译任务。两个标准 Ubuntu 作业，分别 10/15 分钟超时，过时运行取消，令牌只读；官方 actions 固定提交 SHA，不设定时轮询，不上传数据、图片或 PDF artifact。实际远端 CI 状态请查看 Actions 与 PROGRESS，不把本地通过冒充远端通过。
