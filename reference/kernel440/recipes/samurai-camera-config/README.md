# config／stack r27：四摄原厂自动调校发布

已正式安装五个 libcamera 运行包99990.7.2-r32及config／stack0.1.0-r27，匹配434生产CAMSS／ICP core／m2m。包含0042—0050真实PD10、GTM实际版本、成功数学历史与前摄IPE CCM，再以0051修复RAW-only没有IPE消费者时错误强制PD10的问题。既有子包和其它IPA保留。

四摄原生／隔离整合实拍406帧通过。默认四摄GStreamer、RAW／双流、主摄与前摄自动链路及普通用户PipeWire通过；最终部署与适用范围见[440记录](../../../../reference/kernel440/README.md)。原厂表仅在本机私有配置；公共通用YAML内容不变，配置包精确固定r32依赖。完整画质、更多尺寸／视频／HDR和多摄校准继续。

构建输入和实际安装证据见[源锁](source-lock.json)。早期逐帧通道发布记录见[420历史](../../../kernel420/README.md)，不代表当前仍使用旧版旁路调校。
