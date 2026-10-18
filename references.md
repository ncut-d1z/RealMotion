# 载具真实运动约束：资料索引

核查日期：2026-10-18。范围：轮式地面载具、普通共面固定桨轴四旋翼，以及它们对单目 VO 的可用先验。
本清单不是系统综述，也不按引用量或新旧排序。优先选择作者/研究机构、出版社和厂商原始来源。
“已读全文文本”不意味着图表逐项重算；个别 PDF 图像抓取失败不用于提取图中数据。
**论文 PDF、网页快照和厂商手册均不存入本仓库。**

## 阅读路线与实验映射

| 研究问题 | 优先资料 | 本仓库的推导/实验 |
|---|---|---|
| 车轮如何约束机体速度；何时需要轮胎动力学 | P01、P02、M01 | theory 第 3 节；E01、E02 |
| 旋转与帧间平移方向为什么出现“半角” | P03、P04 | 圆弧积分；E02 |
| 相机杆臂能否提供绝对尺度 | P05、P06 | 刚性外参、条件尺度；E04、E06 |
| 运动规律应作硬限制还是概率先验 | P06 | 软约束/创新；E07（仅观测层演示） |
| 为什么四轮固定朝向底盘转弯需要滑移 | P09、M02 | 接触约束秩；E03 |
| 四旋翼的姿态到底约束速度还是加速度 | P07、P08 | Newton–Euler、推力投影、加加速度；E05 |
| 厂商操作限制是否等于机械恒等式 | M01–M03 | 严格区分结构、控制模式、经验上限 |

## 一、期刊论文与会议论文

### P01 — 常规轮式机器人约束分类（期刊）

Campion, G.; Bastin, G.; d’Andréa-Novel, B. **Structural properties and classification of kinematic and dynamic models of wheeled mobile robots.** IEEE Transactions on Robotics and Automation, 12(1), 47–62, 1996.

DOI：<https://doi.org/10.1109/70.481750>

作者机构记录：<https://research.dial.uclouvain.be/entities/publication/f5199cdc-0f43-489b-91b3-9e9eb1ecf7de>

核查范围：机构元数据与摘要；该页面未提供已读取的论文全文。用途：理解车轮类型、运动学约束与可动性分类。本文的接触点速度、约束矩阵和反例为独立推导，不把本条未读全文当成逐式核验。

### P02 — 自行车运动学与动力学模型的适用范围（会议）

Kong, J.; Pfeiffer, M.; Schildbach, G.; Borrelli, F. **Kinematic and dynamic vehicle models for autonomous driving control design.** IEEE Intelligent Vehicles Symposium, 1094–1099, 2015.

DOI：<https://doi.org/10.1109/IVS.2015.7225830>

ETH 机构记录：<https://www.research-collection.ethz.ch/items/fc80b713-96b1-43f3-b546-3fc0a5eb500b>

核查范围：机构元数据与摘要，未通读全文。用途：运动学模型与轮胎动力学模型的选型背景；提醒参考点、速率定义和侧偏角定义不能混用。仓库没有声称复现其控制实验。

### P03 — 道路车辆的一点 RANSAC 单目 VO（会议）

Scaramuzza, D.; Fraundorfer, F.; Siegwart, R. **Real-Time Monocular Visual Odometry for On-Road Vehicles with 1-Point RANSAC.** ICRA, 4293–4299, 2009.

DOI：<https://doi.org/10.1109/ROBOT.2009.5152255>

作者 PDF：<https://rpg.ifi.uzh.ch/docs/ICRA09_scaramuzza.pdf>

核查范围：已读作者 PDF 全文文本。关键联系：在局部车辆运动模型下压缩视觉运动假设空间。必须同时考虑平面/圆弧假设与相机安装位置；不是任意六自由度运动都能用一个点求解。E02 只验证其几何依据，不复现 RANSAC。

### P04 — 非完整约束与一点结构恢复的期刊扩展（期刊）

Scaramuzza, D. **1-Point-RANSAC Structure from Motion for Vehicle-Mounted Cameras by Exploiting Non-holonomic Constraints.** International Journal of Computer Vision, 95, 74–85, 2011.

DOI：<https://doi.org/10.1007/s11263-011-0441-3>

作者 PDF：<https://rpg.ifi.uzh.ch/docs/IJCV11_scaramuzza.pdf>

核查范围：已读全文文本，重点是车辆圆运动与相机位置的模型。用途：区分瞬时无侧向速度与两帧圆弧弦方向，推导 `phi = theta/2` 的有效条件。不得把后轴参考点上的简单公式直接套到任意光心。

### P05 — 已知相机安装几何可打破尺度自由度（会议）

Scaramuzza, D.; Fraundorfer, F.; Pollefeys, M.; Siegwart, R. **Absolute Scale in Structure from Motion from a Single Vehicle Mounted Camera by Exploiting Nonholonomic Constraints.** ICCV, 2009.

作者 PDF：<https://rpg.ifi.uzh.ch/docs/ICCV09_scaramuzza.pdf>

作者研究目录：<https://rpg.ifi.uzh.ch/research_vo.html>

核查范围：已读全文文本。用途：纠正“所有载具先验都不可能帮助单目恢复尺度”的过度概括。已知米制前向杆臂与适当转弯是额外信息；直行、安装退化、滑移和噪声会破坏简单解。E06 给出同类条件下的独立代数验证，不采用论文实车数据。

### P06 — 将非完整运动规律作为概率先验（会议）

Scaramuzza, D.; Censi, A.; Daniilidis, K. **Exploiting Motion Priors in Visual Odometry for Vehicle-Mounted Cameras with Non-holonomic Constraints.** IROS, 2011.

作者 PDF：<https://rpg.ifi.uzh.ch/docs/IROS11_scaramuzza.pdf>

核查范围：已读全文文本。其方法利用运动先验构造提议分布，并放松严格平面/圆运动假设；与仅作硬约束不是一回事。E07 的高斯软融合和创新门控是本仓库独立设计的观测层演示，**不是该论文算法的复现**。

### P08 — 含旋翼阻力的四旋翼平坦性（期刊）

Faessler, M.; Franchi, A.; Scaramuzza, D. **Differential Flatness of Quadrotor Dynamics Subject to Rotor Drag for Accurate Tracking of High-Speed Trajectories.** IEEE Robotics and Automation Letters, 3(2), 620–626, 2018.

DOI：<https://doi.org/10.1109/LRA.2017.2776353>

作者预印本及补充推导：<https://arxiv.org/abs/1712.02402>；<https://arxiv.org/pdf/1712.02402>

作者研究页面：<https://rpg.ifi.uzh.ch/aggressive_flight.html>

核查范围：已读预印本文本并查看动力学公式页图像。用途：姿态—加速度、角速度—更高阶位置导数耦合，以及阻力对模型的影响。论文中存在质量归一化阻力记法；本仓库 `drag_kgps` 是 kg/s 的力系数，**仅实现各向同性线性阻力，不是完整旋翼气动复现**。

### P09 — 四轮滑移转向实验运动学（期刊）

Wang, T.; Wu, Y.; Liang, J.; Han, C.; Chen, J.; Zhao, Q. **Analysis and Experimental Kinematics of a Skid-Steering Wheeled Robot Based on a Laser Scanner Sensor.** Sensors, 15(5), 9681–9702, 2015.

DOI：<https://doi.org/10.3390/s150509681>

出版社全文入口：<https://www.mdpi.com/1424-8220/15/5/9681>

归档入口：<https://pmc.ncbi.nlm.nih.gov/articles/PMC4481911/>

核查范围：出版社检索返回的元数据、摘要与部分正文；直接访问遇到限流，PMC 入口遇到验证页，未通读整篇全文。用途：滑移转向的 ICR/等效参数及工况依赖。四固定轮完全无滑移不能转弯的结论在 theory 中另由接触约束直接证明。

## 二、四旋翼力学补充原始文稿

### P07 — SE(3) 上的四旋翼刚体动力学（作者预印本）

Lee, T.; Leok, M.; McClamroch, N. H. **Control of Complex Maneuvers for a Quadrotor UAV using Geometric Methods on SE(3).** arXiv:1003.2005，2010，修订版 2011。

元数据：<https://arxiv.org/abs/1003.2005>

全文：<https://arxiv.org/pdf/1003.2005>

核查范围：已读全文文本并查看模型/分配矩阵公式页图像。用途：Newton–Euler 方程、推力/力矩输入与姿态演化。该文世界轴与推力正向约定不同；本仓库统一世界 z 向上、推力为 `+f R e3`。不要把此标题直接当作另一篇 CDC 会议论文的相同题名。

## 三、生产厂商公开手册

### M01 — AgileX HUNTER2.0 User Manual

手册入口：<https://agilexrobotics.gitbook.io/hunter-2.0>

结构介绍章节：<https://agilexrobotics.gitbook.io/hunter-2.0/1-hunter-2.0-introduction>

核查范围：已读取官方介绍章节，确认其 Ackermann 转向结构；技术参数图表未逐项读取，因此没有把其中尺寸作为本实验参数。说明普通 Ackermann 四轮底盘与四轮滑移转向不是同一种约束。

### M02 — Clearpath Husky A200 User Manual

官方手册：<https://docs.clearpathrobotics.com/docs_robots/outdoor_robots/husky/a200/user_manual_husky/>

核查范围：官方手册正文，重点为 Robot Equations。它给出左右侧速度与车体线/角速度的降阶关系，并将用于角速度换算的轮距标为有效轮距。几何轮距、有效轮距和不同 Husky 代际不可混用。本实验的 `0.55 / 0.715 m` 是独立构造的几何/有效轮距对，**不是 A200 标定值**。

### M03 — DJI Mini 4 Pro 官方下载页与用户手册

官方入口：<https://www.dji.com/downloads/products/mini-4-pro>

User Manual v1.4，下载页日期 2024-06-27：
<https://dl.djicdn.com/downloads/DJI_Mini_4_Pro/20240627/DJI_Mini_4_Pro_User_Manual_en.pdf>

核查范围：下载页中的版本与 PDF 链接；约 28 MB PDF 超出本次读取限制，**没有通读正文**。此条仅作为后续核查飞行模式、速度/姿态限制和安全工况的厂商入口，不作为本文推力方程、参数或控制器内部实现的证据。

## 四、软件与工程依据

S01 NumPy 独立随机流与 SeedSequence：<https://numpy.org/doc/stable/reference/random/parallel.html>

S02 SciPy 初值积分与成功标志：<https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html>

S03 SciPy Euler 角的单轴批量形状：<https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.from_euler.html>。实现显式使用 `(N, 1)`，避免本地 SciPy 1.17 遇到的一维批量输入歧义。

S04 Matplotlib 面向对象 Agg 渲染：<https://matplotlib.org/stable/gallery/user_interfaces/canvasagg.html>

S05 GitHub Actions 工作流语法：<https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax>

S06 `.gitignore` 上游（根目录合并其生效规则，省略上游注释后另加项目强制规则）：

- Python：<https://github.com/github/gitignore/blob/main/Python.gitignore>，核查 blob `6f596e17917419c463b0d15bf1f0bce19b8918eb`。
- TeX：<https://github.com/github/gitignore/blob/main/TeX.gitignore>，核查 blob `542f7143fc42be08fa365e4e52cd11110a8bf792`。

工作流中的官方 `checkout`、`setup-python` 使用本次从各自上游 tag 解析的完整提交 SHA 固定，不在每次 CI 自动追随浮动 tag。

## 当前证据缺口

没有实测轮胎侧偏刚度、地面附着系数、桨叶气动参数或电机时间常数；没有产品固件内部闭环辨识；没有真实相机像素匹配与尺度漂移实验。P01、P02、P09 和 M03 的读取范围已单独标注。数值一致性验证不能替代这些证据，也不能保证先验对任意车辆/工况都改善 VO。
