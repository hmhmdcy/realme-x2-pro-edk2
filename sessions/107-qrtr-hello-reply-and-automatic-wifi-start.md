# 阶段107：QRTR HELLO应答/公告顺序修复，首次自动Wi-Fi通过

2026-10-11，实际Linux #106；全硬件目标active，尚未完成。

手机已部署Linux #106（阶段107），仅刷logdump；DTB、完整boot分区、CPIO/模块、配置及显示/radio bootconfig字节保留。
QRTR恢复收到远端HELLO后先应答HELLO、再公告服务，移除会丢包返回-EAGAIN的hello_sent门控；保留endpoint初始化/MHI恢复的主动HELLO与既有重试/API。新boot首次14/64/4096三个公告成功，真实固件/RAM COW NV请求、原生PD mapper回复通过，auto worker0，无手动MPSS恢复；5GHz认证/DHCP/网关3/3/DNS/HTTP及切回5GHz复测通过。
2.4GHz单次2462MHz认证、DHCP、网关3/3和DNS通过，收到577字节HTTP内容，但wget20秒未正常退出，完整测试仍失败；本轮未见WRONG_KEY或reason7，历史reason7/删除等待及新HTTP收尾问题保留。首次自动启动已在一轮新boot验证，重复冷启动/休眠/长期稳定仍待验收。
首次音频API7/API2、2秒低音量有限播放与DMIC0回归通过，双功放start1/stop1/failed0；DMIC0 5.04秒/241920帧，稳态非零208180/80种值/无削波，实际声音/质量无人确认。本轮没有core重绑或ADSP重启，106阶段首次100ms重绑成功记录保留。
检查点154文件/七原包及所有SHA通过，首次radio trace无丢失；uptime216.9、首次MPSS连续约171.1秒，双DSP running、taint0、fatal0。本次显示超时1、BT phase2错误2仍在待办；蓝牙停止不配对连接，振动standby/starts0无新脉冲，机械确认暂缓。
下一轮kernel108优先重复干净启动与2.4GHz数据/HTTP收尾，随后继续其它15组。保留Android/data/GPT/NV/persist/SSH/rootfs01/F2FS/旧显示，私人固件/日志/身份/凭据/音频/镜像不公开，不提交推送；全硬件goal active。

## 修复及实机证据

修改仅net/qrtr/af_qrtr.c和ns.c，两对象W=1零警告。根据[阶段106直接trace](106-first-modem-hello-race-and-core-query-tracing.md)，恢复NS的say_hello应答成功后才announce_servers，去掉首次普通包-EAGAIN丢弃门控及无用hello_sent标志。保留ep_lock真实xmit串行、事务流控、READ_ONCE/WRITE_ONCE、未知节点广播过滤、endpoint注册主动HELLO/100ms重试与取消生命周期、qrtr_endpoint_hello及MHI resume调用；不完整回退其它新API，不改变PD mapper、RMTFS/TFTP、固件、NV或启动delay。

[上游原改动](https://github.com/torvalds/linux/commit/544d85de4dc22c01badfd8cefa59829ce35c4858)转移HELLO所有权并删除NS应答；[回退提案](https://lists.openwall.net/linux-kernel/2026/09/18/1409)因其它Wi-Fi休眠回归恢复旧序列。本轮按本机证据做两源有限修正，保留主动初始化/resume接口，不宣称其它平台/MHI实机已验收。

新boot modem HELLO在42.873658秒进入NS，本机应答42.873677秒成功，14/64/4096公告42.873692/42.873705/42.873714秒全部0；kernel/elf_loader真实返回1 domain，随后读取固件与RAM COW NV。endpoint主动HELLO仍保留，两个DSP各有两次合法HELLO，未观察循环风暴。first-radio-trace全CPU overrun/commit-overrun/dropped均0。首次MPSS up 45.801895秒，原auto worker0，检查点连续171.098秒无fatal；没有手动MPSS恢复、core解绑重绑或ADSP重启。这是一轮新boot验证，不能替代重复冷启动/休眠/长期压力。

5GHz先验认证/DHCP/网关3/3/DNS/HTTP577B成功，切回5GHz再次全流程退出正常。2.4GHz2462MHz新连接/握手各1，DHCP成功、网关3/3、DNS成功，HTTP577B内容完整收到但timeout20终止wget，原result保持SINGLE_24G_ATTEMPT_FAILED，不能改判整个流程通过。新wpa日志只有主动换频reason3，没有WRONG_KEY/reason7；原件与最终5G分别保存，旧reason7仍是历史待办。下一轮结合TCP关闭/重传及HTTP响应结束边界定位，不先猜密码或NV损坏。

首次原生core API7/API2回归，阶段106非阻塞trace与100ms修复保持；本轮未重复core重绑。有限播放退出0/无错误，PCM关闭，双功放start1/stop1/failed0/global00；DMIC0偏置/MCLK On至Off、5.04秒采样、稳态无削波。物理声音/拾音质量无人确认，历史DMIC1/2保留，振动无新脉冲，蓝牙不配对连接。

Image `9a3a8180f7199c06841ce78561a793f546d363df27b76c9b600a825ed7d7ef17`，DTB `2a9e3cac62e7f6b8eb767230b630ddbeee546535acf9eec225bf3591dd623cbb`，CPIO `71f0fac2cb4251214ba33c86bf332e2367cbaf676f877c4030d1228e71c64ae7`；候选logdump `6f75695e38eb46dcebd2046f29f950cca24ed6d8fce315ec2b0709353c4c4c7f`，完整boot `d1f81ebc4dc9687b705cffe38ecde93b8c4cd60a4c37463901b7cf7b900e1278`。两源以外全部tracked/untracked源码、配置、原bootconfig、初始文件/模块/DTB字节保持；NV六区/persist/stock DTBO和实际FDT校验通过，FDT仅UEFI chosen允许字段不同。DTB相同，只刷logdump一次，不重建/刷boot。

新80备份块中boot-040传输连接重置，未完成块保留.partial-first，校验已收块后恢复并完整拼接；设备当时双DSP running/taint0。F1回执后首次fastboot枚举未就绪，脚本在任何write前停止；新enumeration-late前缀独立确认身份/大小/候选SHA后才只写logdump。失败原件全部保留，USBipd保持Running，EUD最终detached，不forcebind未知hrdevmon。

检查点 SHA `62dfd166ac909bc46cca464e13ad88ee28cf3f98561cee17d4fe4c68e52ea59c`，154文件/七原包及全部嵌套SHA/原件逐字节通过；公开15组及F2FS段落保留，凭据/身份/固件/日志/录音/镜像只在本机私有输出。不提交推送。下一輪见[交接](../reference/kernel107/next-session.md)及[15组状态](../linux-port/docs/HARDWARE-STATUS.md)。
