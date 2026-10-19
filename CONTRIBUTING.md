# 开发约定

Python 3.10+，在项目根目录运行 `python -m pip install -e ".[dev]"` 和 `python -m pytest`。
修改接口需同步 examples、README 与对应行为测试。硬件适配需注明系统、驱动、模型、后端版本。
结果必须保留原始逐请求/逐任务记录、配置和随机种子；不提交 API Key、模型权重或私人数据。
本仓库为 AI 辅助开发的个人研究原型，欢迎通过 issue 记录复现环境和失败输入。
