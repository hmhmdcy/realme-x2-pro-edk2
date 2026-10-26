# 224：相机RAW统计与停止取消修复

2026-10-16。完整libcamera r11/config-r6安装通过，保留boot219/Image183/e49/fae1。0015补CPU RAW-only自动统计和曝光/增益元数据；0016/17修复相同实机生命周期探针依次找到的重复取消断言、未处理RGB取消状态。r9/r10失败及产物保留，未部署。

安装后128帧普通/隔离IPA、RAW/RGB实验16MP各36帧、cam/GStreamer各6帧、同相机五次重配40请求通过。最终相机电源关闭、DSP正常、taint/fault0、NV源保持；16MP实验开关已关。没有刷写/重启、外部照明或保存场景。后置四摄、手动API、真实画质与整机其它外设继续开放。

[完整记录](../reference/kernel224/README.md)、[补丁配方](../linux-port/packages/libcamera/README.md)、[当前检查点](../NEXT-SESSION.md)。
