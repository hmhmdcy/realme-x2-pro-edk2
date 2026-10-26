# 369：取得真实 A5 故障快照，错误仍未收敛；恢复相机基线

本轮针对368的新核心做一次独立实验，目标为保全真实SFR及核查错误清理。未重放366。收集器先启动并写就绪记录，再加载临时boot诊断模块；核心与368实际产物完全相同（232352字节），临时诊断模块另加强残留时钟／电源域的module pin条件。两模块按k363实际in-tree W=1/-Werror构建，无诊断。[构建](intree-build-validation.json)、[资源归属模型](ownership-validation.json)。静态DT／原厂ELF与366相同，没有改已安装的VFE、传感器、IPA、包或个体配置。

收集器只接受本次新增、failing_device与临时A5设备／OF节点同时匹配的devcoredump；原始记录及解码文件fsync后才确认消费，以便释放快照持有的设备引用。夹具中验证了实际独立进程先就绪、无关设备不被消费、有界格式解码、落盘先于确认和无快照时的超时。[夹具](collector-validation.json)。这不代替内核框架实际回收证明。

## 实际结果

实验再次造成新Linux启动，原worker没有正常终态。独立收集进程在重启前留下了完整568字节devcoredump，已从设备取回并离线解析：HFI响应3、版本寄存器0x01000100、三个队列read/write均0、interrupt/watchdog/protocol-error计数均0，SFR正文为空。原始快照SHA256为`b3ca6c91f52aefee242e46efba0c5c02b7f6e46f08b18d9564fd998139a3f7bd`，只私存。

ramoops证明CPU release后2.711ms即读到3，expired=0，随后记录block reset asserted。新快照路径实际执行并成功保留数据，但未观察到collector完成／确认消费，也未观察到DMA撤销／断电的完整终态。本轮末尾没有足够日志证明重启原因，不能把366的modem watchdog标签自动移植到这次失败。**完整SYS_INIT/PING/PC_ACK仍未通过；先退DMA后断电尚未获得真实成功清理证明，不能称watchdog已修复。** [有限证据](boot-runtime-r1-validation.json)。旧`state.json`的terminal=false及raw快照保留。

## 恢复与内存核对

通过既有严格原密钥Wi-Fi确认新启动；旧worker、collector、ICP模块和临时DT节点均不存在，17路ICP/BPS/IPE时钟为0，taint0。boot366/logdump365读回保持；临时firmware副本只在与原厂／事务副本哈希一致后删除，旧事务与原件保留。[新启动](recovered-boot-validation.json)、[清理](recovery-cleanup-validation.json)。SSC、SensorProxy、greetd、Phoc/Phosh及PW/WP已正常启动，因此未再额外重启或刷写。

在该启动只读9ab00000专用固件区首个4KiB代码页，仍不匹配已知ELF，遂未读取异常状态页，不能据此恢复故障寄存器。另只查询这5MiB／1280页的内核分配元数据：全部为保留页，mapcount0，没有slab、buddy、匿名映射或页表占用。[分配状态](firmware-reservation-validation.json)。这只排除已观察启动中的Linux普通页分配占用，不能证明其它固件／安全世界所有权或A5实际访问权限。

恢复后四颗已确认传感器各12帧GStreamer，主摄隔离IPA另28帧／五控制阶段和Gamma回执通过；相关新故障0，九相机电源disabled/users0、CAMSS/双CCI休眠。[采集](camera-runtime-validation.json)。十个相机相关模块loaded note与磁盘一致，无活动实验worker、ICP模块、临时固件或动态节点，taint0，PW/WP各一个uid10000。[最终状态](final-state-validation.json)。本轮没有NV／OTP／个体校准分区写入，没有发送主机系统复位；原始数据和完整日志均只私存。

## 下一步

停止重复同一CPU启动／错误清理序列。先离线核查A5自己的MMU／共享区／SFR映射及CSR读回语义；设计将CPU quiesce与DMA撤销／断电明确分开的诊断窗口，在停止后的已拥有固件RAM中保全异常状态，之后才能做新的针对性硬件检查。不能用空SFR、已发布快照或模型通过替代握手／清理验证。

仍需完整ICP／IPE会话及IO/IQ接入、未知2MP人像摄像头身份、更多模式和完整光学／几何／同步／连续AF。整体goal保持active。
