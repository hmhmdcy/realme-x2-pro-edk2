> 最新见[阶段106](../../sessions/106-first-modem-hello-race-and-core-query-tracing.md)及[当前交接](../kernel106/next-session.md)。下文保留105历史；106 core首次100ms重绑查询通过，首次MPSS失败有HELLO/公告trace证据，修复尚未部署。

# 下一阶段：优先首次MPSS请求链与APR日志时限

当前[session105](../../sessions/105-apr-rebind-and-first-modem-crash-smem-diagnostics.md)与[15组状态](../../linux-port/docs/HARDWARE-STATUS.md)。全硬件goal active，无预算、尚未完成。

手机已部署Linux #104（阶段105），本轮仅刷logdump；DTB、整个boot分区、原CPIO/模块/无线/显示源码保留。
APR服务登记移至每次driver probe，解绑先移除登记并等待在途APR回调；修正包头长度边界。core查询使用非零事务token，只接受匹配回复，合法版本成功才缓存，未知basic错误不当unsupported，超时明确返回。首次原生回复AFE API7/ASM API2；一次正常core重绑后收到合法回复，第一次100ms查询仍超时，EUD读取期间一次有界复测通过，超时原件保留。
首次MPSS约40秒fatal仍未修复：SMEM421全局/调制解调器私有区均返回-ENOENT，崩溃原因项不存在。首轮没有来自modem的TFTP/RMTFS读写请求，原worker1与失败完整保留；唯一手动恢复后，同一组RAM COW服务收到真实请求，5GHz认证/DHCP/DNS/HTTP/网关3/3通过。
2秒-48.16dBFS有限播放回归退出0、双功放start1/stop1/failed0；DMIC0回归5.04秒/241920帧，非零230051，稳态208265非零/80种值/0削波，偏置和MCLK正常关闭；历史三路DMIC采样保留，实际声音和拾音质量仍无人确认。蓝牙保持停止、不配对连接；振动standby/starts0，无新脉冲，机械确认暂缓。
149文件检查点/八原包及全部SHA、新80块备份、完整分区读回与实际FDT/NV/persist/stock DTBO保留通过。检查点uptime444.61、恢复MPSS连续约279.8秒，双DSP running、taint0，历史首轮MPSS fatal1/ADSP0、显示超时4、BT phase2错误1。
下一轮优先首次MPSS启动的QRTR/GLINK/原生PD mapper请求链，检查core诊断日志与100ms时限相互影响，随后继续15组硬件。保留Android/data/GPT/NV/persist/SSH/rootfs01/F2FS/旧显示，固件/日志/身份/凭据/音频/镜像留本机，不提交推送；全硬件goal active。

下一轮kernel106/全新输出前缀；当前私人kernel105/runtime-boot-id-after-private.txt及checkpoint SHA `f14b32a972043f32cb6d80e1b608581441dceaa78945a5cb3da8126ec17211f5`绑定真实#104。八原包全部校验，tests/checkpoint-validation.json有149文件、第一次core重绑超时及后续成功边界。只执行一次core重绑、一次MPSS恢复，ADSP无重启。

首次WiFi失败没有modem TFTP/RMTFS请求；SMEM421全局/host1 ENOENT，不能称已取得fatal原因。原生SM8150 PD mapper映射、server_check RAM支持既有，勿盲复制其它机型region/永久PD电压floor或延长delay。下步补board-only、有限的PD mapper请求/回复、QRTR/GLINK事件并比较首轮/恢复；必须保存原auto worker1，只有有界恢复能作为当前5G证据，2.4GHz reason7仍未修复。

APR初始FWK116字节/API7/API2通过，driver正常重绑后登记与packet回复恢复，但第一次100ms sysfs读取超时；EUD reader期间一次有界复测通过。检查q6core callback在complete之前的诊断输出可能阻塞，优先将诊断置于完成之后或用不阻塞的trace；这是待证解释。不要把status22说成ENOTREADY或unsupported，当前缓存只存合法版本，命令/token严格匹配。无需重复重绑或ADSP restart。

当前实际源码/home/cy122/x2pro-linux/linux；DTS与reference/kernel104/sm8150-samurai.dts.after一致，新增三C源与kernel105/*.c.after一致。DTB/CPIO相同、完整boot未刷，本轮只logdump；未来若改DTB必须真重建EDK2嵌入DTB。配置/旧源码/模块/所有旧显示快照保持，linux-port/dts旧镜像故意不覆盖。

MPSS用/usr/sbin/samurai-modem-remoteproc完整OF与固件定位，不固定remoteproc编号；ADSP qcom/sm8150/realme/samurai/adsp.mdt。amps1-0039/1-003a归驱动，GPIO148/37不要重新直接操控；WCD143、QUP4 GPIO51/52、QUAT137–139和触屏54保持。motor唯一driver/89c000 OF，现2-005a starts0无新脉冲。5G私有配置kernel105/wpa-5g-private.conf限制5180，不要用kernel95的2462配置。

DMIC0回归5.04秒非零230051、稳态208265非零/80种值/无削波；DMIC1/2保留104历史。两个PCM关闭，功放global00/amp80/start1stop1failed0；实际声音/已知声源质量无人确认，勿称完整音频可用。振动按用户日志/静态分析推进，不提问/不重放脉冲；BT保持停止不配对连接；NFC仅控制器。

保留Android/data/userdata/GPT/NV/persist/SSH/rootfs01/F2FS/显示85–88所有内容。只刷boot/logdump，DTB不变优先logdump；每轮全新完整两分区备份。NV RAM COW，不持久写。充电收尾不再执行旧OEM/NV/OTP/unseal/FET/OTG/MCU/GPIO/I2C_FORCE探针。所有固件/原日志/身份/凭据/音频/镜像私人，公开仅自写/GPL修改与脱敏记录，不提交推送。USBipd保持Running，EUD最终detached，hrdevmon警告保留、不forcebind。继续15组硬件优先无线可靠性。
