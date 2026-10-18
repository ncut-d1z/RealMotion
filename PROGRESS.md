# RealMotion 研究与实现进度

更新日期：2026-10-18。起点：`de96454a7d0f463a58d8faf1ce6fb4a375ce36a3`（只有 TODO.md）。

## 不可违反的约束

- 面向无 IMU 单目 VO；不把真实尺度、控制输入或重力方向当成默认可用观测。
- 区分刚体恒等式、理想无滑移、动力学、控制/统计近似；明确相机外参与杆臂。
- 四轮滑移转向不等于四轮完全无滑移；条件尺度恢复不等于一般单目无条件恢复尺度。
- Python 源码与配置入库；数据、插图、PDF、日志、缓存不入库。
- 每次实验独立随机流、独立输出、原子发布，失败只清理本次暂存目录。
- CI 最小权限、有限超时；不设定时轮询、大规格 runner 或产物上传。

## 当前清单

- [x] 读取远端树并保留 TODO.md；先建立本进度文件。
- [x] 完成 references.md：9 篇研究条目（含 1 篇作者预印本）、3 个厂商手册入口及软件资料。
- [x] 逐条标注读取范围；未通读的资料没有冒充已通读。
- [x] 完成 theory.tex：ctexart、统一符号、机械推导、条件尺度、软约束与限制。
- [x] 完成七组 NumPy/SciPy 实验、9 张 Matplotlib 图及 TOML 配置。
- [x] 本地 77 项自动测试通过：解析解、雅可比、退化、参数、重复/并发、失败隔离及强制入库拦截。
- [x] 正式配置与 smoke 已执行；结果概要写入 README。
- [x] 本地 XeLaTeX/latexmk 成功编译 12 页；日志检查无错误、缺字、未定义引用或 overfull box。
- [x] 检视论文页面及 9 张图的渲染，未发现截断/错位。
- [x] 合并 Python/TeX 上游生效 gitignore 规则，新增数据/图片禁止规则和 tracked-file 检查器。
- [x] 写好 GitHub Actions：标准 Ubuntu 两个作业，固定官方 action SHA，10/15 分钟超时。
- [x] 整体提交已验证源文件并回读远端树/哈希（首次 24 个文件全部一致）。
- [x] 已读取最终远端 Actions 的两个作业与完整日志：Python 和 LaTeX 均 success。

## 工作日志

### 阶段 0：建立进度边界

读取仓库元数据和完整树；仅有 TODO.md，默认 main。创建本文件的提交为 `0c8ca8b05efc39c86f0805ef7fb38784f97a1c47`，在验证前不声称通过。

### 阶段 1：资料和首轮仿真

已读 Scaramuzza 的 ICRA 2009、IJCV 2011、ICCV 2009、IROS 2011 作者 PDF 文本，Lee 四旋翼及 Faessler 阻力模型；部分公式页图像已查看。Campion、Kong 只核查机构元数据；Wang 滑移论文只有出版社检索正文片段；DJI PDF 约 28 MB，未通读。以上均在 references.md 单独标注。

首次 smoke 发现 SciPy 1.17 单轴批量 Euler 角需明确 (N,1) 形状，已修复。随后七组 smoke 全部成功并绘图。阶段记录已独立提交为 `c4d186661ecad49f53f992d498a3425b5d0ab7a0`。

### 阶段 2：数值、文件策略与文档验证

本地环境：Python 3.13.5 / NumPy 2.3.5 / SciPy 1.17.0 / Matplotlib 3.10.8 / pytest 9.0.2。

实际执行：`python -m pytest -q`（76 passed）；`python -m compileall -q realmotion scripts tests`；`python -m realmotion --config configs/default.toml`；`latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error theory.tex`；两个 scripts 检查器。

默认正式配置核对：

- E01 最大位置差 1.75e-14 m；E02 恒曲率半角 RMSE 5.51e-13°，误用初始方向为 3.543°。
- E04 有限外参恒等式误差 1.78e-15 m。
- E05 忽略阻力的横向比加速度残差最大 1.774 m/s²。
- E06 条件尺度 3.7000000000000015；真实含阻力却忽略时偏为 5.68098；悬停拒绝输出尺度。
- E07 5° 失配：原始/硬/软/门控方向 RMSE 分别约 2.005°/5.006°/4.644°/4.233°。

这些是合成实现与假设验证，不是实车精度或论文算法复现。新增 E02 非局部圆弧拒绝测试，防止把短弦方向结论套到大于等于 pi 的帧间转角。

数值/图像/PDF/日志只在本地忽略目录，不进入待提交源文件集合。

### 阶段 3：远端核查与 CI 解析修复

完整源码提交 `0ca1f1a4464464c13f7da15cfa53167e7ce5b22d` 已更新 main；24 个远端文件的 Git blob SHA 与本地已验证源文件逐项相同，TODO.md 保持原 SHA。

首次远端运行 <https://github.com/ncut-d1z/RealMotion/actions/runs/39120251146> 在作业创建前失败（jobs 为空）。核对 GitHub 官方 context availability 表，确认 job-level env 不支持 runner 上下文；原先在该位置使用了 runner.temp。现改为运行步骤通过 RUNNER_TEMP 写入 GITHUB_ENV，并增加防回归测试；本地再次执行 77 项测试通过。官方说明：<https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability>。

修复提交：`d7444f4c1b4512cdd7e37fca0956e07d1ad830b4`。第二次运行：<https://github.com/ncut-d1z/RealMotion/actions/runs/39120425866>。

已读取远端 Python 作业 `117654741160` 的实际日志：77 passed in 5.70s；compileall、七组 smoke 与全部绘图、入库检查及工作区无修改检查均通过。LaTeX 作业在编译时失败；已读取日志，确认精简安装缺少 hyperref 的 pzdr.tfm 字体度量文件。

远端官方 action 日志另有 Node.js 20 弃用及强制切换 Node.js 24 的警告；不影响本次 Python 成功，但后续维护应评审更新 action 的固定提交。这里没有把有警告的日志称为“完全零警告”。

### 阶段 4：精简 TeX 环境修复

第二次运行的 LaTeX 日志明确报告 pzdr.tfm 缺失。修复为显式安装 texlive-fonts-recommended，并在编译前用 kpsewhich 检查 pzdr.tfm 和 FandolSong-Regular.otf；README 的 Ubuntu 安装命令同步更新。不删除 hyperref 或关闭错误检查来掩盖缺失依赖。

### 阶段 5：最终远端 CI 通过与交付核对

修复字体依赖的代码提交：`cd708d614963ae4795d325694472bd25cc61662b`。最终验证运行：<https://github.com/ncut-d1z/RealMotion/actions/runs/39120730505>。

已读取该运行的作业状态和两个完整日志：

- Python 作业 `117655634413`：success，`77 passed in 5.86s`；静态编译、七组 smoke 与绘图、源文件白名单、工作区无修改检查全部通过。
- LaTeX 作业 `117655634228`：success；两个字体文件预检成功；latexmk 自动完成三轮 XeLaTeX 和 PDF 转换，生成 12 页文档；最终日志检查和源文件政策检查通过。
- 最终 LaTeX 日志没有编译错误、缺字、未定义引用或 overfull box；仍有 Fandol Script CJK 元数据警告和两处 underfull hbox 提示。它们未使编译失败，不宣称日志完全无警告。

README 安装说明随后在纯文档提交 `27c80639e746f069697b509d0c20c752dcb17a07` 同步更新；本进度更新也只改 Markdown，不修改已验证的程序、理论正文或工作流，不重复触发 CI。

当前交付共 24 个源文件/配置/文档；首次整体远端 blob 校验全部一致，后续 workflow、README、测试文件也按返回的 blob SHA 与本地逐项核对。TODO.md 内容和原 SHA 不变。最终 Python/LaTeX 两个 runner 都确认没有生成物被跟踪或意外修改源码。

本地生成的 PDF 和 9 张图另行提供下载，不进入 Git，也不上传 GitHub Actions artifact。资料、源码、配置、运行说明和证据边界均已提交；未完成的后续研究见下节。

## 明确保留的研究缺口

没有完整像素级 VO、真实轮胎/桨叶参数辨识、道路/风场实验、未知重力鲁棒联合尺度估计或 FastMono 后端接入。接下来的实车工作必须单独采集数据和验证，不能用理想方程的零残差代替。

### 阶段 6：跨平台一键运行入口（2026-10-18）

- [x] 新增根目录 `run.sh`（可执行位）和 `run.ps1`，定位脚本目录，创建/复用 `.venv`，验证 Python 3.13+、latexmk/xelatex/kpsewhich 和必需字体。
- [x] 顺序执行开发依赖安装、Git checkout 下的源文件政策检查、Python 静态编译、pytest、smoke、full、XeLaTeX 与最终日志校验；任何错误中止。
- [x] 源文件白名单显式放行根目录两个启动脚本，不放宽对其他 `.sh`/`.ps1` 的限制；新增 `tests/test_launchers.py` 检查。
- [x] README 已更新 Linux/Windows 用法和预先安装系统级 TeX 工具的条件。
- [x] 以并发新增的 `PROMPT.md` 为最新基底提交，未覆盖该文件。运行脚本代码提交：`544fdc906e28bca922005f0c3dcc0e4052bc31dc`。
- [x] 远端 CI Python 作业通过（包含新增启动脚本检查）。
- [x] 本轮 GitHub Actions Python 与 LaTeX 作业均 success：<https://github.com/ncut-d1z/RealMotion/actions/runs/39122069891>。
- [ ] 新的一键脚本自身在 Windows PowerShell 和用户本机尚未端到端实测；不把 CI 中执行的原有 Python/TeX 命令等同于跨平台脚本验证。

本次新增脚本有操作系统差异：Windows 需要正确配置 TeX 的 PATH；Linux 需要 `python3-venv` 及字体包。脚本不会使用 sudo、apt、强制清理旧产物或上传文件。`run.sh` 本身的 shell 解析与 `run.ps1` 的 PowerShell 解析仍需在各目标系统验证，不能将 Python CI 等同于跨平台端到端测试。

### 阶段 7：学术文字与数学符号可读性（2026-10-18）

- [x] 已读取 main 最新 theory.tex 原文，确认原文无独立实验数值表、图仅为命令行生成（未在 TeX 中嵌入）。
- [ ] 逐节为首次出现的专业概念和公式变量增添单独释义，所有方程先文字总结后列式。
- [ ] 完善两张现有表格的自足 caption，补充带加粗重点数据的实验摘要表。
- [ ] 将参考文献调用统一为上标方括号数字式；检查引用序号与编译。
- [ ] 读取 GitHub Actions latex 作业状态和日志，失败则修复。
