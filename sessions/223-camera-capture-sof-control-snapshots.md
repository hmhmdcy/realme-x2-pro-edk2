# 223：SOF捕获号与控制快照配套部署

2026-10-16，CAMSS fae1与libcamera r8/config-r3已安装，boot219/Image183/IMX471 e49保持。修复间断请求后采集号连续计数和误用请求号读取曝光历史的问题。160帧临时缓冲/SOF配对、128帧普通/隔离IPA捕获控制关联、36帧实验16MP换算及默认cam/GStreamer通过。

关灯4MP RAW/RGB数值统计有帧间变化、无全零帧；没有保存场景或使用外部照明。原82c模块及实际r7/r2七包保留，最终taint/fault0。标准手动曝光、物理延迟、后置四摄、GNSS真实定位及其它外设继续开放。

[完整记录](../reference/kernel223/README.md)、[最终验收](../reference/kernel223/final-validation.json)、[当前检查点](../NEXT-SESSION.md)、[硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。
