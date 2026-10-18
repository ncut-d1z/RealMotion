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
- [x] 本地 76 项自动测试通过：解析解、雅可比、退化、参数、重复/并发、失败隔离及强制入库拦截。
- [x] 正式配置与 smoke 已执行；结果概要写入 README。
- [x] 本地 XeLaTeX/latexmk 成功编译 12 页；日志检查无错误、缺字、未定义引用或 overfull box。
- [x] 检视论文页面及 9 张图的渲染，未发现截断/错位。
- [x] 合并 Python/TeX 上游生效 gitignore 规则，新增数据/图片禁止规则和 tracked-file 检查器。
- [x] 写好 GitHub Actions：标准 Ubuntu 两个作业，固定官方 action SHA，10/15 分钟超时。
- [ ] 整体提交已验证源文件并回读远端树/哈希。
- [ ] 读取实际远端 Actions 结果；本地通过不代表远端通过。

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

## 明确保留的研究缺口

没有完整像素级 VO、真实轮胎/桨叶参数辨识、道路/风场实验、未知重力鲁棒联合尺度估计或 FastMono 后端接入。接下来的实车工作必须单独采集数据和验证，不能用理想方程的零残差代替。
