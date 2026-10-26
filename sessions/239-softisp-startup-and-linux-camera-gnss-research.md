# 239：软件 ISP 首参修复与 Linux 摄像头/GNSS 搜索

2026-10-16。r15/config-r10已完整构建、实际七包升级及默认路径两次start验参；前摄RAW/RGB各六帧回归通过。RAW/RGB同request统计解释BLC剪裁，但后摄零帧严格失败与光学/颜色问题保留。

补齐当前ODM gps.conf来源及S5K3M5的917初始化/212模式写入核验；再查Realme X3、OPPO Reno、一加7T Pro/6及Surface Duo、上游相同传感器实现。GNSS未发现可直接部署RF修复，仍无真实fix。无场景保存、加光、GNSS SET、搜星、刷写或重启，完整goal active。

[实现与验证](../reference/kernel239/README.md)、[机型与Linux使用方法](../reference/kernel239/RELATED-LINUX-SOLUTIONS.md)、[检查点](../NEXT-SESSION.md)。
