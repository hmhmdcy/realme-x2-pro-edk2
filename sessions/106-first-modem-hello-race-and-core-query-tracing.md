# 阶段106：首次modem HELLO/服务公告竞态有直接trace证据

2026-10-11，真实Linux #105；全硬件目标active，尚未完成。

手机已部署Linux #105（阶段106），仅刷logdump；DTB、整个boot分区、CPIO/模块及原显示bootconfig字节保留，独立radio trace记录协议元数据。
首次无线失败已定位到HELLO/公告顺序：modem HELLO到来时本机HELLO尚未发送成功，第一条服务公告返回-EAGAIN并终止全部公告，57.368毫秒后HELLO成功但公告不补发；首轮无modem固件/NV请求，auto worker1和约40秒fatal仍保留。唯一手动恢复时HELLO先成功、三个公告全成功，同一组原TFTP/RAM COW服务收到请求，5GHz认证/DHCP/网关3/3/DNS/HTTP通过。顺序缺陷已观测，修复尚未部署，不能称冷启动可靠性已解决。
音频core诊断改用完成后的内存trace，原100ms时限保留；首次API7/API2、一次正常core解绑重绑后的首次查询均通过，测试期间EUD reader未运行，ADSP未重启。2秒低音量有限播放通过，双功放start1/stop1/failed0；DMIC0回归5.04秒/241920帧，稳态非零209233/242种值/无削波，偏置和MCLK正常关闭，实际声音/拾音质量无人确认。
检查点194文件/八原包及所有SHA通过，三段trace均无丢失。uptime419.82、恢复MPSS连续约168.6秒，双DSP running、taint0；首轮MPSS fatal1/ADSP0，本次显示超时0，历史问题保留，BT phase2错误3。蓝牙保持停止、不配对连接，振动standby/starts0，无新脉冲，机械确认暂缓。
下一輪kernel107优先修复QRTR收到HELLO后公告被门控丢弃的顺序，保持HELLO先行且补全服务公告；不得猜NV、延长启动delay或无界重启DSP。2.4GHz/休眠/长期稳定及其它15组待办继续。保留Android/data/GPT/NV/persist/SSH/rootfs01/F2FS/旧显示，私人固件/日志/身份/凭据/音频/镜像不公开，不提交推送；全硬件goal active。

## 原件与源码边界

首次trace在启动时启用，无console tp_printk；独立radio实例1MB/CPU，原display实例512KB/CPU与snapshot配置字节保留。[内核启动trace文档](https://docs.kernel.org/trace/boottime-trace.html)支持实例与事件组，实际/proc/bootconfig、三段每CPU统计均入原包。只记录QRTR/GLINK头信息、native PD mapper响应与core事务结果，不记录无线密钥或数据载荷。

五个已有源码修改及一个新trace头：net/qrtr/smd.c、af_qrtr.c、include/trace/events/qrtr.h、drivers/soc/qcom/qcom_pd_mapper.c、sound/soc/qcom/qdsp6/q6core.c、include/trace/events/samurai_diag.h。SMD提前发布drvdata并检查endpoint就绪，修复静态初始化窗口，本轮没有观测RX drop，不能说这是首次崩溃原因。QRTR发送trace记录xmit前真实wire_node；PD mapper在响应与解锁后记录元数据，映射/协议未改。core移除完成前的同步dev_info，改为完成后trace；无延长100ms，无ADSP重启。W=1零警告。

首轮modem HELLO在43.999204秒进入NS，公告14于43.999213秒被hello_sent门控返回-11；44.056581秒本机HELLO才成功，之后无补发。ns.c的announce_servers遇到错误立即退出，64/4096也未发送。首次无来自modem的PD mapper/固件/NV请求。MPSS up 46.782194秒，fatal诊断86.628971秒；SMEM421全局/host1仍ENOENT，不能称取得DSP fatal文本。

唯一恢复trace：248.455291秒本机HELLO成功，248.455445秒NS处理远端HELLO，14/64/4096三个公告均返回0。原TFTP/RMTFS PID未变化，随后真实kernel/elf_loader返回1 domain并读取固件、RAM COW NV，MPSS up 251.247621秒，5GHz实测通过。两个启动顺序解释首次服务缺失；修复尚未部署，需要下一轮A/B实证。

[Qualcomm作者HELLO改动](https://lists.openwall.net/linux-kernel/2026/08/27/989)将握手移到endpoint注册并门控普通包；[上游审查](https://lists.openwall.net/linux-kernel/2026/08/18/304)讨论入站HELLO时公告也可能被门控；[回退提案](https://lists.openwall.net/linux-kernel/2026/09/18/1409)针对其它Wi-Fi休眠回归恢复NS应答。提案/其它设备报告不等于本机验证，后续按本机直接trace修正，不盲改NV、PD映射或电压。

首次音频FWK回复116字节/token1。一次core正常重绑后首次回复与等待结果均0、API7/API2；trace phase1/phase2在245.771959/245.771961秒，但这2微秒只是完成通知至等待返回间隔，不是完整查询耗时。未运行EUD reader，未追加复测/ADSP重启。有限播放与DMIC0验证见八原包，实际声音质量未知；DMIC1/2保留104历史。

Image `b5292d4aee0985b0c4b140cb7bf265ee29da24bd63c83d86e5df81a3b647afa8`；DTB `2a9e3cac62e7f6b8eb767230b630ddbeee546535acf9eec225bf3591dd623cbb`；CPIO `71f0fac2cb4251214ba33c86bf332e2367cbaf676f877c4030d1228e71c64ae7`。logdump `fbaeefb50b395b71f6968663248237b6f271f50db2fb8509374a9ec17ca6b5d8`；完整boot `d1f81ebc4dc9687b705cffe38ecde93b8c4cd60a4c37463901b7cf7b900e1278` 未改写，实际FDT仅UEFI chosen允许字段不同。NV六区、persist、stock DTBO字节保留，新80块备份均SHA通过。DTB相同，无需重新构建或刷EDK2 boot。

检查点 SHA `5b1f64ad5b6274dc5f59730620f76c2c5f20d1b06acc15558b0ddb6c77ddc070`；194文件包括八原包及全部嵌套SHA/原包逐字节核验。F1后USB消失导致reader EIO/退挂无设备，原件保留，已收F1并独立fastboot确认后才仅刷logdump。早期boot-finished/tracefs尚未出现与host读取单行bootID误取首字符的前置guard失败无设备修改，已用完整bootID重做。最初检查点以模块加载列表逐字节比较失败：早期BT辅助模块3个、用户要求stop后0个；CPIO/模块二进制仍字节相同，修正为检查该明确生命周期变化，原包不改。

## 下一轮

kernel107全新boot/PID/prefix和完整备份，优先修复HELLO未完成时NS公告丢弃，保持HELLO先行、顺序完成后公告。三段trace原件留私有目录，不能重放旧guards。首次auto1不改写为成功，当前只可称恢复后5G通过；2.4GHz/删除等待/冷启动/休眠/长稳仍待办。蓝牙不配对连接，振动无需实物反馈，NFC仅控制器。保留Android/data/GPT/NV/persist/rootfs01/F2FS/SSH/旧显示；充电收尾，不再执行旧OEM/OTP/unseal/FET/OTG/MCU/GPIO/I2C_FORCE探针；不提交推送。详见[15组状态](../linux-port/docs/HARDWARE-STATUS.md)与[最新交接](../reference/kernel106/next-session.md)。
