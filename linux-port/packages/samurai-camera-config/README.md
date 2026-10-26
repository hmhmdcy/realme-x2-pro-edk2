# 四摄原厂自动调校：当前实装与配方历史

2026-10-24：[484](../../../reference/kernel484/README.md)已实装libcamera r33及config／stack r28，441三ISP模块＋468 sensor＋四原厂私有profile，真实升级／精确回退／再升级均成功。[490](../../../reference/kernel490/README.md)的r34／r29七包和精确r33／r28回退仅离线就绪，未安装；[491交接](../../../reference/kernel491/HANDOFF.md)记录暂停状态及恢复步骤。下文及本目录原配方保留440 r32／r27发布历史，不冒充已更新为候选recipe。

已正式安装五个 libcamera 运行包99990.7.2-r32及config／stack0.1.0-r27，匹配434生产CAMSS／ICP core／m2m。包含0042—0050真实PD10、GTM实际版本、成功数学历史与前摄IPE CCM，再以0051修复RAW-only没有IPE消费者时错误强制PD10的问题。既有子包和其它IPA保留。

四摄原生／隔离整合实拍406帧通过。默认四摄GStreamer、RAW／双流、主摄与前摄自动链路及普通用户PipeWire通过；最终部署与适用范围见[440记录](../../../reference/kernel440/README.md)。原厂表仅在本机私有配置；公共通用YAML内容不变，配置包精确固定r32依赖。完整画质、更多尺寸／视频／HDR和多摄校准继续。

构建输入和实际安装证据见[源锁](source-lock.json)。早期逐帧通道发布记录见[420历史](../../../reference/kernel420/README.md)，不代表当前仍使用旧版旁路调校。

后续参数与模式扩展按[原厂资料优先工作流](../../docs/PORTING-WORKFLOW.md)执行：复用已提取表和个体数据，缺项再提取/反编译或搜索公开仓库，只验证受影响模式。
