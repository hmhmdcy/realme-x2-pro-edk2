# 226：GNSS原始测量与辅助对照

默认/HIGH×辅助前后四轮各90秒，固件HIGH读回3；现有helper一次UTC/文件注入使有效期0→168h，XTRA debug掩码0→31，仍无正CNR/TRACK/真实fix。诊断支持扩展SV/NMEA且缺失不作0，debug此次仅证明PQWP7扩展路径，不冒称标准定位流已修。

全部原生会话与QMI客户端正常清理，GPS空闲/刷新30，三DSP running、taint/fault0、NV源保持；boot219/e49/fae1/r13保持，未刷写/重启。117成员最终私人归档核对。用户无SIM、室内窗边关灯，后摄、BT、传感器、蜂窝业务和全外设goal继续。[完整报告](../reference/kernel226/README.md)、[检查点](../NEXT-SESSION.md)。
