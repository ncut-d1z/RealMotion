[$github](app://connector_76869538009648d5b282a4bb21c3d157)&#x20;

我正在研究的单目视觉里程计，没有讨论过四旋翼无人机、四轮车等具体载具的运动规律。我想这些载具的旋转与平移之间一定有某种规律，这两种运动不可能是自由的、无约束的。

按照以下两条思路帮我整理资料，修改 [https://github.com/ncut-d1z/RealMotion](https://github.com/ncut-d1z/RealMotion) 仓库：

- 搜索期刊论文、会议论文、生产厂商公开发布的手册，将搜集的资料的URL写入根目录下文件 references.md 中；
- 根据运动学、机械原理，进行理论公式推导，并写入 theory.tex 文件中（使用 ctexart 文档类）。
- 根据 references.md 中的资料 和 theory.tex 提供的理论推导 ，利用 Numpy/Scipy 进行仿真实验，用 matplotlib 绘图。要求：脚本具有高度可重入性；所有 python 脚本与相关的配置文件都必须写入仓库，但是数据文件（包括但不限于 \*.npz, \*.csv 等）、插图文件（包括但不限于 \*.png, \*.jpg 等）不可以进入仓库。
- 执行上述任务时，创建、修改 PROGRESS.md 文件，用于自查当前任务进度，避免长时间工作出现幻觉
- 使用 [https://github.com/github/gitignore/blob/main/Python.gitignore](https://github.com/github/gitignore/blob/main/Python.gitignore) 和 [https://github.com/github/gitignore/blob/main/TeX.gitignore](https://github.com/github/gitignore/blob/main/TeX.gitignore) 等管理不需要上传到仓库的数据；另外还需要根据之前的规定（禁止数据文件、插图文件进入仓库）修改根目录 .gitignore 文件
- 合理使用 github actions workflows 帮助排查 LaTeX 文档编译期间的任何错误，帮助清查 python 脚本的运行时异常
