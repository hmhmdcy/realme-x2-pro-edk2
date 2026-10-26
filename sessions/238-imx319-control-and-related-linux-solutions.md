# 238：IMX319控制链与近机型Linux方案

2026-10-16。完整r14/r9候选已构建和RAM暂存，IMX319 48帧RAW曝光/增益控制通过；RGB程序完成48帧但启动q1为全零，严格验收失败、未默认安装。原生证据和失败保留，供电/图/PM/时钟恢复，taint/fault0。

重新核对Realme X2 Pro、OPPO Reno、一加7T Pro/6及Surface Duo的摄像头/GNSS使用路径；离线核真实vendor GNSS初始化，尚无可部署RF修复。未存场景、未加照明、未搜星/SET、未重启/刷写，完整goal active。

[实现与验证](../reference/kernel238/README.md)、[机型与源码对照](../reference/kernel238/RELATED-LINUX-SOLUTIONS.md)、[当前检查点](../NEXT-SESSION.md)。
