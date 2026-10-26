# 366：将静态 ICP 板级引用装入实际 EDK2 固件 DT

复用276已验证的固件构建、FFS/压缩载荷核对和boot封装流程，以365已核对的DT替换固件卷内DT。逐FFS模块比较：只有DTB模块变化，其它固件代码与数据完全一致；shim、ramdisk、Android头、兼容DT和分区尾部保持，30条既有诊断模板没有新增。仓库DT和三个共享固件输出在退出时恢复。[构建](build-package-validation.json)。

候选boot使用同一Image363／模块树／362调校用户空间，logdump365不再改写。实际切换、摄像头回归与A5实验结果以各验证JSON为准，不能以候选构建通过替代运行证明。固件及原厂ELF字节只私存。

boot366启动读回通过，Linux实际出现禁用ICP节点及正确5MiB固件引用；四颗已确认传感器各12帧GStreamer，主摄隔离IPA另27帧／五控制阶段通过，服务和相机电源恢复，taint0。[实际DT](postboot-validation.json)、[切换后采集](camera-runtime-r2-validation.json)。r1在正常桌面启动完成前因无PipeWire退出，未进行媒体操作，失败保留。

随后一次A5实验没有正常终态，设备发生异常重启。新启动从原密钥Wi-Fi可达，ramoops证明：正确物理预留区解析、固件及共享IOVA映射和上电均完成，CPU已释放；HFI响应持续3，在500ms精确等待期限内未到1，记录超时和block reset asserted；约1秒后modem watchdog。**没有完整SYS_INIT/PING/PC_ACK，没有观察到完整清理终态，watchdog因果尚未证明。** [有限日志证据](boot-runtime-r1-validation.json)。不能把旧state的terminal=false改成成功，也不能据寄存器版本值宣布固件可用。

异常重启后旧worker、实验模块和临时节点均不在，17路ICP/BPS/IPE时钟归零、taint0。已核对boot/logdump，按哈希只移除临时`/lib/firmware`副本，保留原ELF和事务原件；新boot guard独立建立。[恢复与清理](recovery-cleanup-validation.json)。EUD只开启COM作15秒被动读取，未发送终端字节或系统复位，随后关闭COM并释放USB转发。一次Windows静态USB地址设置被系统拒绝，未改变主机网络设置；恢复使用已有严格密钥Wi-Fi端点。

恢复启动的SSC file server exit4，SLPI已自行回滚到offline、电源关闭，桌面因SSC依赖未启动，r3采集因此在取流前退出。367执行不刷分区的正常重启恢复基线，不重新释放A5 CPU。下一步先离线追踪原厂response3写入、CSR/HFI语义与停机次序，再设计新的有针对性的硬件检查；不重复此次启动。
