# 200：静态MMCX成对启动与前摄跨启动回归

静态四域DT与CAMSS已成对部署，新boot四轮12帧真实RAW10、运行时384→0通过，最终taint0且所列内核/蓝牙fault全0。第一会话MCLK下拉恢复失败、单独原值恢复，以及第二会话sleep pull-down修复后的完整恢复均保留。蓝牙8秒只扫描、三项传感器Claim/Release与USB归档通过；完整外设goal继续。

详细源码/失败/回退/验收边界见[阶段200报告](../reference/kernel200/README.md)，当前组合见[检查点](../NEXT-SESSION.md)，未完成项目见[硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。
