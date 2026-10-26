# 484 实际安装独立审计

481 三次原生 APK 事务和 482 两轮 14 个默认路径用例的实际原件已通过独立缓存审计。结论、原始失败分类和范围见 [HARDWARE.md](HARDWARE.md)，可复核计数见 [hardware-validation.json](hardware-validation.json)。

本地复审入口：`inspect-installed.py --private-root PRIVATE481 --output NEW_RECEIPT`。只读取缓存，并复用冻结 482 的纯日志历史检查器；不导入或执行 target callback。输出必须使用新路径，以保留历史回执。私有 world、调校系数和 maps 不复制至公开结果。
