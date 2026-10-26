> 最新见[阶段107](../../sessions/107-qrtr-hello-reply-and-automatic-wifi-start.md)与[当前交接](../kernel107/next-session.md)。下文保留106失败历史，107已部署HELLO应答/公告修复并首次auto0/5G通过。

# 下一阶段：修复QRTR HELLO/服务公告顺序

当前[session106](../../sessions/106-first-modem-hello-race-and-core-query-tracing.md)与[15组状态](../../linux-port/docs/HARDWARE-STATUS.md)。全硬件goal active，无预算。

手机已部署Linux #105（阶段106），仅刷logdump；DTB、整个boot分区、CPIO/模块及原显示bootconfig字节保留，独立radio trace记录协议元数据。
首次无线失败已定位到HELLO/公告顺序：modem HELLO到来时本机HELLO尚未发送成功，第一条服务公告返回-EAGAIN并终止全部公告，57.368毫秒后HELLO成功但公告不补发；首轮无modem固件/NV请求，auto worker1和约40秒fatal仍保留。唯一手动恢复时HELLO先成功、三个公告全成功，同一组原TFTP/RAM COW服务收到请求，5GHz认证/DHCP/网关3/3/DNS/HTTP通过。顺序缺陷已观测，修复尚未部署，不能称冷启动可靠性已解决。
音频core诊断改用完成后的内存trace，原100ms时限保留；首次API7/API2、一次正常core解绑重绑后的首次查询均通过，测试期间EUD reader未运行，ADSP未重启。2秒低音量有限播放通过，双功放start1/stop1/failed0；DMIC0回归5.04秒/241920帧，稳态非零209233/242种值/无削波，偏置和MCLK正常关闭，实际声音/拾音质量无人确认。
检查点194文件/八原包及所有SHA通过，三段trace均无丢失。uptime419.82、恢复MPSS连续约168.6秒，双DSP running、taint0；首轮MPSS fatal1/ADSP0，本次显示超时0，历史问题保留，BT phase2错误3。蓝牙保持停止、不配对连接，振动standby/starts0，无新脉冲，机械确认暂缓。
下一輪kernel107优先修复QRTR收到HELLO后公告被门控丢弃的顺序，保持HELLO先行且补全服务公告；不得猜NV、延长启动delay或无界重启DSP。2.4GHz/休眠/长期稳定及其它15组待办继续。保留Android/data/GPT/NV/persist/SSH/rootfs01/F2FS/旧显示，私人固件/日志/身份/凭据/音频/镜像不公开，不提交推送；全硬件goal active。

当前私人kernel106/runtime-boot-id-after-private.txt绑定#105，checkpoint SHA `5b1f64ad5b6274dc5f59730620f76c2c5f20d1b06acc15558b0ddb6c77ddc070`、194文件/八原包。next kernel107、新prefix，不能重放本轮已存在的目录、core重绑或MPSS恢复；本轮各一次，ADSP无重启。

直接证据：首轮HELLO43.999204，公告-11在43.999213，本机HELLO44.056581，公告未重试；恢复本机HELLO248.455291先行，三个公告成功，same TFTP/RMTFS PID、kernel/elf_loader及真实读写请求恢复。三个trace零丢失，原件first-radio-trace/core-rebind-once/radio-recovery-first.tar。ns.c仍未修改，只诊断；优先在HELLO与公告之间实现顺序保证/应答或可靠重试，不硬编码modem node0、不盲改NV/PD mapper/region/delay。上游HELLO v3和回退提案均在session链接，不能把提案视为已合并。

实际源码/home/cy122/x2pro-linux/linux；DTS与kernel104镜像相同，新增源码与kernel106/*.after和samurai-diag.h一致。只有CONFIG_BOOT_CONFIG_EMBED_FILE改为kernel106私有radio-bootconfig.txt，保留旧display前缀、无tp_printk。DTB/CPIO模块/原boot完全相同，本轮logdump-only；未来DTB改动必须真重建EDK2嵌入DTB。

core诊断不再同步dev_info，首次及一次正常重绑后首次100ms查询都API7/API2通过，无EUD reader/no ADSP restart。2微秒只代表phase1/phase2间隔，不能称完整耗时。旧105首次超时留历史。

MPSS用/usr/sbin/samurai-modem-remoteproc完整OF与固件定位，不固定remoteproc编号；ADSP qcom/sm8150/realme/samurai/adsp.mdt。amps1-0039/1-003a归驱动，GPIO148/37不要重新直接操控；WCD143、QUP4 GPIO51/52、QUAT137–139和触屏54保持。motor唯一driver/89c000 OF，现2-005a starts0无新脉冲。5G私有配置kernel106/wpa-5g-private.conf限制5180，不要用kernel95的2462配置。

DMIC0回归5.04秒非零231139、稳态209233非零/242种值/无削波；DMIC1/2保留104历史。两个PCM关闭，功放global00/amp80/start1stop1failed0；实际声音/已知声源质量无人确认，勿称完整音频可用。振动按用户日志/静态分析推进，不提问/不重放脉冲；BT保持停止不配对连接；NFC仅控制器。

保留Android/data/userdata/GPT/NV/persist/SSH/rootfs01/F2FS/显示85–88所有内容。只刷boot/logdump，DTB不变优先logdump；每轮全新完整两分区备份。NV RAM COW，不持久写。充电收尾不再执行旧OEM/NV/OTP/unseal/FET/OTG/MCU/GPIO/I2C_FORCE探针。所有固件/原日志/身份/凭据/音频/镜像私人，公开仅自写/GPL修改与脱敏记录，不提交推送。USBipd保持Running，EUD最终detached，hrdevmon警告保留、不forcebind。继续15组硬件优先无线可靠性。

