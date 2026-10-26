# 373：A5就绪与SYS_INIT实机通过，probe退出阶段仍重启

本轮承接372取得的原厂异常现场，将HFI参数编程移动到CPU复位、唤醒之后，初始化请求之前；逐一读回10个寄存器，任一不符则拒绝提交INIT_REQUEST。顺序对照已保存原厂`cam_hfi_enable_cpu`及`cam_hfi_init`。不修改原厂固件去绕过错误，也不允许响应3继续发SYS_INIT。[补丁](hfi-reset-order.patch)。

**真实结果：A5响应由3变为就绪1，约5.532ms；10个参数读回通过，SYS_INIT已确认。** 随后生产PC_PREP／WFI路径记录pc_error=0、DMA aliases retired、PM reference released:0。之后仍进入新启动，旧worker停在load-boot-test、terminal=false，没有取得完整probe／卸载终态。PING没有独立持久化回执，因此不宣称完整SYS_INIT/PING/PC_ACK或硬件清理验收完成。[实机证据](boot-runtime-r1-validation.json)。

这是SoC A5启动顺序的真实功能进展；没有测得旧顺序下CSR在复位前后的数值，不能把“复位清空参数”当已证实机制。参数顺序改变后SYS_INIT成功是已有直接结果。正常start成功未调用失败快照，不是372观察器失效。当前仍有后续重启，不能据此部署成正式ICP/IPE后端。

实际编程helper／start函数体模型检查参数写入在reset/wake之后、初始化请求之前；读回不符不会提交初始化。旧代码顺序反例被拒绝，实际start的13路径模型也通过，MMIO／PM／固件回复为桩。[顺序](order-validation.json)、[生命周期](lifecycle-validation.json)。两个实际k363 in-tree W=1/-Werror模块无诊断，test与372逐字节同一。维护分支`samurai-a5-hfi-reset-order373`，最终提交`1e495f16e41b6a8198555a2c5f41b71c63527ea9`，父372 `71ca6b...`；中间提交另保留。[构建](intree-build-validation.json)、[源码](source-state.json)。

本轮只修改SoC传输核心、临时诊断owner与工具；板级DT／保留内存、主线OF/IOMMU、CAMSS/VFE／传感器和正式libcamera／IPA／校准配置未改。核查实际dt-binding和CAMCC实现：reset ID9确为CAM_CC_ICP_BCR、映射c0b4；没有盲改其它复位或全局fw_devlink策略。

## 恢复后的当前设备

当前guard `/var/lib/samurai/k373-recovered/boot-id-private.txt`，后续用host373，严格原密钥USB。实际仍Image363、boot366／DT365、libcamera r29／config r24和362四份私有Preview默认。boot/logdump读回保持；临时firmware在与原厂和事务副本hash相同后删除，旧事务与原件保留。候选模块未永久安装，随新启动消失，默认静态ICP仍disabled。[恢复](recovered-boot-validation.json)、[清理](recovery-cleanup-validation.json)。没有主机复位、刷写、NV／OTP／校准分区写入。

SSC、SensorProxy、greetd、Phoc/Phosh和adsp/slpi/modem正常；PW/WP在启动稍后自行出现，未额外重启或手工创建重复服务。[健康](current-health-validation.json)。四颗传感器各12帧硬件采集通过，主摄隔离IPA另27帧／5阶段和Gamma ACK通过，相关新增故障0。[采集](camera-runtime-validation.json)。十个相关模块loaded note匹配磁盘，CAMSS/双CCI休眠、九相机电源disabled/users0、PW/WP各一个uid10000、taint0，无worker／ICP模块／临时固件／动态节点。[终态](final-state-validation.json)。

## 后续

保留本轮复位／唤醒后配置及读回，不再重演旧初始化参数故障。下一步补齐PING、PC_ACK、probe返回前结果的持久化证据，定点跟踪退出／绑定完成后的runtime PM、supplier和sync_state，区分CPU块复位、资源清理与主线设备框架阶段；当前精确重启原因未知。不能把fw_devlink代理错误或PM函数返回0单独当作根因或完整清理成功。

完整HFI生命周期、IPE图像会话与IO/IQ及libcamera后级接入、第五颗2MP身份、更多模式、光学／几何同步／连续AF等仍未完成，见[剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)。整体目标继续active。
