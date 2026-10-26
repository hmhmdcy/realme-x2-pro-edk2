# 237 IMX319首批RAW与CAMSS失败回收

2026-10-16。移植并部署CAMSS失败回收修正ff9，IMX319取得6帧1632×1224 RAW10；前摄RAW/CPU RGB各6帧回归，全图/控制/供电/PM恢复、taint/fault0。后摄接近黑电平，光学响应/曝光及RGB待验，未保存场景。两次Popen前的工具失败保留。

[实现和原生证据](../reference/kernel237/README.md)、[检查点](../NEXT-SESSION.md)、[GNSS核对](../reference/kernel237/GNSS-FOLLOWUP.md)。
