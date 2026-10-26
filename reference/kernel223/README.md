# 223：捕获帧与控制快照配对已部署

2026-10-16，当前为boot219/Image183/IMX471 e49、CAMSS fae1、完整libcamera99990.7.2-r8/config0.1.0-r3。本轮没有重启或刷写。[安装](coherent-install-validation.json)、[最终健康](final-health-validation.json)、[部署锁](../../linux-port/camera/deployment-lock.json)。全外设goal继续active。

原驱动RAW请求间隔500ms时，缓冲号仍连续0–15；原r7 RGB请求4对应buffer33，却用请求索引读取曝光历史。新CAMSS用真实SOF标记每个缓冲，重新排队清有效位，缺标记交付buffer error，仅SM8150/VFE170订阅FRAME_SYNC。完成时间戳仍为EOF；IRQ掩码、时钟和电源策略保持。[补丁](camss-sm8150-paired-sof-candidate.patch)、[原RAW基线](baseline-raw-gap-validation.json)。

新libcamera在捕获回调按采集号读取DelayedControls并保留独立快照，统计处理使用此副本；IPA上下文仍用请求号，无frameStart平台保留原路径。[用户态补丁](libcamera-capture-control-snapshot.patch)。这次配套部署解决已复现的采集帧/曝光历史关联错误，尚未加入标准手动曝光API。

临时内核试验2MP/4MP RAW/RGB共64帧，配套r8另做96帧，均能在独立事件流找到每个缓冲的SOF，没有缺标记。r8的64帧RGB在普通/隔离IPA均验证采集号与控制索引一致，曝光换算误差小于1µs。临时试验均先恢复82c，之后才配套安装fae1/r8。[内核试验](paired-sof-native-validation.json)、[配套试验](control-snapshot-native-validation.json)。这些证据不代替光学曝光延迟标定。

安装后普通/隔离IPA另64帧间断请求通过；实验16MP另36帧元数据换算通过，已恢复实验参数N及WP。默认cam/GStreamer各6帧通过。原771个其他模块文件、944包中的937个无关记录、49相机payload/权限复核通过；world仅更新stack版本。[安装后控制](installed-control-validation.json)、[16MP](exposure-metadata-system-r8-4608x3456-validation.json)、[GStreamer](standard-gstreamer-validation.json)。

关灯条件下真实4MP RAW、RGB各6帧只在内存统计：RAW值62–133、标准差2.656–2.666，相邻帧约56.2%像素变化，RAW/RGB全零帧均为0。这批样本包含暗光信号及噪声，未复现固定全零输出；不据此验收颜色、曝光质量或所有镜头。[暗帧分类](dark-frame-classification-validation.json)。没有保存场景图像、闪光或外部照明。

完整13包保留全部原13补丁、全部子包/管线/tuning，签名、34个ARM64 ELF、5IPA匹配核心公钥及Qt/Python入口通过。原214构建树2254个文件/链接/权限及内核180份源/对象/模式恢复，原r7对象缓存保留。私钥仍为原214/203外部输入，未进入包或仓库。[完整产物](forward-package-artifact-validation.json)、[运行入口](host-runtime-qa-validation.json)。二次逐字重建未验证。

原82c模块在设备k223-r8-paired-deployment及本轮私人证据中；实际七个r7/r2回退包仍在k220-r7-package-candidates，降级模拟通过，未执行完整回退往返。首个安装后验证器误把/run测试可执行文件当成候选库，16帧本身成功；已保留失败记录，改为仅检查库映射并用新目录完成回归。[验证器修正](installed-validator-correction.json)。

标准手动曝光/增益/独立Auto/Manual尚未加入；RAW-only仍绕过SWISP配置和统计，不能只验RGB就宣称完整API。真实CFA/几何/颜色/物理延迟、后置四摄和GPU ISP故障仍开放。GNSS仍无真实fix/正CNR；蜂窝业务、蓝牙phase5、传感器SSR等按[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)继续。两槽状态引用221历史记录，不是本轮重新查询。
