# 394：真实帧 ACK 丢失触发重启；保留证据并恢复正式四摄

本轮受控丢弃一条经校验的真实IPE帧ACK，实际进入5.142701秒完成超时。ramoops证明超时时映射和两个导入引用仍保留，随后A5强制块复位返回、两路IPE复位确认均为[3,3]；日志在完整DMA退映射之前中断，设备自行重启。**故障恢复实验失败，不能把复位确认或后续正常四摄恢复算作完整错误恢复通过。**

已核对新启动的boot389/logdump365、393正式核心／adapter及个体配置；临时测试参数消失，生产磁盘文件未变。新启动四摄各12帧默认r30 GStreamer通过、资源回收、服务恢复。完整目标继续active。

## 方法与分层

沿用既有仓库／方案调查、原厂ELF/HAL协议反编译与393实际驱动。现运行内核未启CONFIG_FAULT_INJECTION；依据[内核故障注入说明](https://docs.kernel.org/fault-injection/fault-injection.html)中模块局部配置思路，仅构建一份临时测试核心，从私有路径加载，没有替换根文件系统正式模块、DT、FW或用户空间。

[临时补丁](temporary-ack-loss.patch)受CAMSS_A5_TEST_DROP_FRAME_ACK编译宏控制。默认不丢ACK，两个上下文各自完成一帧且session并存后，客户端只设置一次模块参数。真实ACK经过既有尺寸、type、opcode、双token与成功状态检查后，原子消费开关、不唤醒等待者；没有修改DMA地址／命令内容、IRQ mask、超时长度或复位实现。另加两个只读日志点观察超时前后引用及IPE复位确认。

[7个实际解析器用例](hook-validation.json)ASan/UBSan通过，错误token、失败ACK、非帧ACK、错误尺寸和未等待消息不消费开关；删除测试宏块复现393原生产文件。[临时核心ARM64构建](intree-build-validation.json)W=1/-Werror通过，诊断0。核心357456字节、SHAb40200a0e9903451a8528a29d1df535b17b5c25adf1d6882f196e0b0aeeee2a3，只是测试产物。

正式维护源source354仍samurai-ipe-errors393/64aaf4f78c05f0912e658780294fbded531d87ce；临时构建结束后源、配置和既有输出已恢复，最终git干净。正式核心仍e22253916088e58a221c1948f025c44c939c819310c7d3f67106053dd39502f6，adapter仍ff2bfa7a9439b2ef67087ff6f5db8c9d26e9a92596cd1f63b14c3a047111d4c1。没有把故障开关留进生产构建。

## 硬件实际证据与失败边界

[故障审计](fault-experiment-validation.json)来自重启前console-ramoops。旧启动最后一个实验窗口：

|阶段|实际证据|
|---|---|
|两上下文预热|两个独立session创建／配置，两次正常硬件帧完成|
|一次ACK丢失|5780.728684记录丢弃已校验帧ACK|
|原生产超时|5785.871385，ret=-110、queued=1、pending=1|
|超时返回前|pending1、request_mapped1、input_ref1、output_ref1|
|A5停机|cooperative0、block_reset1|
|两路IPE复位后／退映射前|reset_acks3,3，pending0、request_mapped0，两个导入引用仍各1|
|完整退映射和PM释放|本次窗口无完成日志；随后启动ID改变|

这证明真实完成超时和保留引用分支已在硬件上触发，以及错误后两路IPE取得复位确认；未证明客户端错误传播、第三上下文拒绝、重新打开恢复、完整DMA退映射或PM释放。测试帧有成功固件ACK但上层未收到，不将它计作正常交付帧，更不能据此证明全部物理硬件故障恢复。

USB SSH观察失败后先核对枚举，确认NCM恢复，再用原密钥raw SSH检查实际启动变化；没有重新启动原worker、重启／刷写手机或重新授权密钥。新启动旧PID13432不存在，故旧启动进程被真实重启终止；不是因一次观察超时就假定进程已结束。

重启后原实验目录只保留已阶段化文件和collector-ready，state、launch、运行日志和collector-result未完整落盘。因此旧worker的清理／collector终态未观察到，不伪造terminal成功，也不能以缺少结果文件证明某一步未执行。206061字节ramoops和本次启动完整日志已私存，未清空pstore。下一次故障实验须先提高状态／日志落盘持久性，并先修正或证明恢复顺序；本轮不重复注入。

## 原厂路径审计与待修复项

[原厂源审计](recovery-source-audit.json)逐摘要验证已保留的Realme GPL9668fcdc6ec15be7a10d66f7b93c347829e0fdb6：352的hfi.c，以及355的cam_icp_hw_mgr.c，未重复下载原件。

直接恢复函数先接管GDSC并复位IPE/BPS；CPU关闭函数执行WFI轮询及本地A5 CSR序列，所检查函数中没有直接assert全局ICP_BCR。现393非协作错误路径先assert全局ICP块，再确认IPE复位并退映射。[375](../kernel375/README.md)已实测正常停机去掉额外全局块复位后可完整返回；394显示错误停机仍在相近边界重启。

这些证据将下一步定位收敛到全局复位、总线可访问性及退映射顺序，**不是已经证明精确重启机制**。没有panic／调用栈／最后PC证明具体故障指令，原厂资源deinit间接调用链也未审完。不能仅删reset、忽略错误或提前归还DMA来让测试变绿。后续必须保持CPU停机可证、IPE新复位确认、未知映射引用保留，并核查原厂完整恢复／资源退出序列。

## 新启动恢复与当前状态

[启动核验](postboot-validation.json)读回boot389和logdump365精确匹配、正常393两模块磁盘与加载note匹配、CAMSS复合模块及adapter note保持、四份私有配置摘要保持，测试参数不存在、taint0，probe不启动FW。原USB密钥／known_hosts不变。新guard=/var/lib/samurai/k394-recovered/boot-id-private.txt；现在使用host394。旧390guard已失效，不能继续用host393旧guard或重授权。

[新启动四摄验证](camera-recovery-validation.json)：imx471/imx319/s5k3m5/s5kgw1各12帧640×480 NV12、正常IPE共48，bus错误0，fixture恢复，无私有库或配置覆盖。新epoch jobs/completed/direct48，failed/cancel/first_error0，starts/stops4；与旧393计数和失败故障窗口分开。黑场／噪点按用户关灯条件解释，不以画面亮度判链路。

[最终状态](current-state-validation.json)：正式393核心、adapter、FW和r30/r25保持，临时测试核心不在内存、磁盘正式模块未替换，维护源干净；CPU/IRQ/PM/backing/map/import全回收，ICP/CAMSS/双CCI suspended，17相关时钟0、九路电源disabled/users0。PW6411/WP6417各一、uid10000；owner_refs53是正常桌面CAMSS句柄，m2m users0。恢复窗口worker6370、client和collector均终态，无新dump／fault、taint0。这里的正常状态通过与原故障实验失败分别记录；未宣称旧SSC间歇故障修复或全平台健康。

## 接续

优先审完原厂强制／恢复停机与资源退出，修复全局ICP块复位到退映射边界，再有针对性验证完成丢失／硬件错误并发。随后推进原厂Gamma/LTM/CCM完整IQ和[363全部范围](../kernel363/REMAINING-CAMERA-SCOPE.md)：第五2MP、多模式、动态帧长／防频闪、几何／多摄同步、连续AF与光学画质。仍1:1 NV12/NV21 IQ旁路，异步implicit-fence发布未证明，总目标未完成。

393原pair备份、391用户空间r29/r24七包、390完整平台／boot366回退资料保持。新启动未刷分区，未执行那些回退。旧故障目录和测试模块只作私有证据留存，runtime工具禁止在已核实重启后重新launch故障实验。FW/HAL/OEM源码/ASM/CDM/全日志/图像/个体数据只private394及前序；公共镜像仅本地提交，不push/PR。
