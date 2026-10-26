from pathlib import Path
import json,re
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel106';out=Path('/mnt/e/edk2-samurai-out/kernel106')
v=json.loads((out/'checkpoint-validation.json').read_text());t=json.loads((out/'tests-validation.json').read_text());k=json.loads((out/'kernel-validation.json').read_text());c=json.loads((out/'candidate-validation.json').read_text())
assert v['checkpoint_archive_audit_pass'] and v['first_hello_service_announcement_race_observed'] and v['first_rebind_query_within_100ms_pass']
targets=['README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md','NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','HANDOVER-NEXT.md','DOCS-INDEX.md','reference/kernel105/next-session.md']
assert not (out/'public-docs-before.json').exists()
before={n:(root/n).read_text() for n in targets};(out/'public-docs-before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2)+'\n')
name='106-first-modem-hello-race-and-core-query-tracing.md'
m=t['microphones'][0]
common=f'''手机已部署Linux #105（阶段106），仅刷logdump；DTB、整个boot分区、CPIO/模块及原显示bootconfig字节保留，独立radio trace记录协议元数据。
首次无线失败已定位到HELLO/公告顺序：modem HELLO到来时本机HELLO尚未发送成功，第一条服务公告返回-EAGAIN并终止全部公告，57.368毫秒后HELLO成功但公告不补发；首轮无modem固件/NV请求，auto worker1和约40秒fatal仍保留。唯一手动恢复时HELLO先成功、三个公告全成功，同一组原TFTP/RAM COW服务收到请求，5GHz认证/DHCP/网关3/3/DNS/HTTP通过。顺序缺陷已观测，修复尚未部署，不能称冷启动可靠性已解决。
音频core诊断改用完成后的内存trace，原100ms时限保留；首次API7/API2、一次正常core解绑重绑后的首次查询均通过，测试期间EUD reader未运行，ADSP未重启。2秒低音量有限播放通过，双功放start1/stop1/failed0；DMIC0回归{m['seconds']}秒/{m['frames']}帧，稳态非零{m['steady_nonzero']}/{m['steady_distinct']}种值/无削波，偏置和MCLK正常关闭，实际声音/拾音质量无人确认。
检查点{v['private_files_verified']}文件/八原包及所有SHA通过，三段trace均无丢失。uptime{v['uptime_seconds']}、恢复MPSS连续约{v['mpss_running_seconds']:.1f}秒，双DSP running、taint0；首轮MPSS fatal1/ADSP0，本次显示超时{v['display_timeouts']}，历史问题保留，BT phase2错误{v['bt_phase2_errors']}。蓝牙保持停止、不配对连接，振动standby/starts0，无新脉冲，机械确认暂缓。
下一輪kernel107优先修复QRTR收到HELLO后公告被门控丢弃的顺序，保持HELLO先行且补全服务公告；不得猜NV、延长启动delay或无界重启DSP。2.4GHz/休眠/长期稳定及其它15组待办继续。保留Android/data/GPT/NV/persist/SSH/rootfs01/F2FS/旧显示，私人固件/日志/身份/凭据/音频/镜像不公开，不提交推送；全硬件goal active。'''
for n in ['README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md']:
    s=before[n];a=s.index('手机已部署Linux #104（阶段105）');b=s.index('全硬件goal active。',a)+len('全硬件goal active。')
    s=s[:a]+common+s[b:];s=s.replace('session105','session106',1).replace('105-apr-rebind-and-first-modem-crash-smem-diagnostics.md',name,1)
    (root/n).write_text(s)
p=root/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text()
rows={
'原生显示面板':f'历史面板/触屏记录保留；#105检查点frame-done timeout{v["display_timeouts"]}、taint0，不据此称已修复 | 保留85–88失败快照，继续查DPU/DSI中断与休眠',
'普通USB与OTG':'CDC NCM/high-speed、系统UsbNcm/密钥SSH/SCP及EUD共存已实测；新80备份块/完整boot不变及logdump读回通过 | OTG/外设、USB3、休眠恢复和长期稳定性',
'Wi-Fi':'历史双频扫描/认证/TCP哈希保留；#105 trace直接观测HELLO未完成导致公告-EAGAIN丢弃，首次auto1/约40秒fatal；唯一恢复后5GHz认证/DHCP/网关3/3/DNS/HTTP通过 | 优先修复HELLO/服务公告顺序并重新验证首次启动；2.4GHz reason7/删除等待/冷启动/休眠/长期稳定待修',
'蓝牙':f'历史附近扫描通过；#105 phase2错误{v["bt_phase2_errors"]}，HCI为空/辅助模块已正常卸载，保持停止 | 用户暂缓配对连接；保留传输错误待办',
'音频':'原生声卡/双MAX98937/WCD934x及有限播放、DMIC0非零采样回归通过；API7/API2及core一次正常重绑后的首次100ms查询通过，诊断不再同步输出 | 实际声音/拾音质量/启动瞬态/耳机/DSM/校准/休眠未验收，旧105首次超时记录保留',
'蜂窝网络/数据':'MPSS/RAM COW基础保留；#105首次约40秒fatal，HELLO/服务公告丢失有直接trace证据，唯一恢复后持续running | 通话/移动数据未验收；原NV不写，优先修复首次请求链',
'振动':'AW8697原生FF/close/SIGKILL/watchdog历史电气验收保留；#105 ID97/standby/starts0/error0，无新脉冲 | 用户暂缓机械确认，按日志和静态分析推进下一项；保持唯一driver/OF身份检查'}
for label,value in rows.items():
    s,n=re.subn(r'^\| '+re.escape(label)+r' \|[^\n]+$','| '+label+' | '+value+' |',s,flags=re.M);assert n==1
s=s.replace('下一项优先首次MPSS请求链、APR查询日志/时限与其它硬件；','下一项优先QRTR HELLO/服务公告顺序与其它硬件；',1);p.write_text(s)
(root/'sessions'/name).write_text(f'''# 阶段106：首次modem HELLO/服务公告竞态有直接trace证据

2026-10-11，真实Linux #105；全硬件目标active，尚未完成。

{common}

## 原件与源码边界

首次trace在启动时启用，无console tp_printk；独立radio实例1MB/CPU，原display实例512KB/CPU与snapshot配置字节保留。[内核启动trace文档](https://docs.kernel.org/trace/boottime-trace.html)支持实例与事件组，实际/proc/bootconfig、三段每CPU统计均入原包。只记录QRTR/GLINK头信息、native PD mapper响应与core事务结果，不记录无线密钥或数据载荷。

五个已有源码修改及一个新trace头：net/qrtr/smd.c、af_qrtr.c、include/trace/events/qrtr.h、drivers/soc/qcom/qcom_pd_mapper.c、sound/soc/qcom/qdsp6/q6core.c、include/trace/events/samurai_diag.h。SMD提前发布drvdata并检查endpoint就绪，修复静态初始化窗口，本轮没有观测RX drop，不能说这是首次崩溃原因。QRTR发送trace记录xmit前真实wire_node；PD mapper在响应与解锁后记录元数据，映射/协议未改。core移除完成前的同步dev_info，改为完成后trace；无延长100ms，无ADSP重启。W=1零警告。

首轮modem HELLO在43.999204秒进入NS，公告14于43.999213秒被hello_sent门控返回-11；44.056581秒本机HELLO才成功，之后无补发。ns.c的announce_servers遇到错误立即退出，64/4096也未发送。首次无来自modem的PD mapper/固件/NV请求。MPSS up {v['first_mpss_up_seconds']}秒，fatal诊断{v['first_mpss_fatal_seconds']}秒；SMEM421全局/host1仍ENOENT，不能称取得DSP fatal文本。

唯一恢复trace：248.455291秒本机HELLO成功，248.455445秒NS处理远端HELLO，14/64/4096三个公告均返回0。原TFTP/RMTFS PID未变化，随后真实kernel/elf_loader返回1 domain并读取固件、RAM COW NV，MPSS up {v['recovered_mpss_up_seconds']}秒，5GHz实测通过。两个启动顺序解释首次服务缺失；修复尚未部署，需要下一轮A/B实证。

[Qualcomm作者HELLO改动](https://lists.openwall.net/linux-kernel/2026/08/27/989)将握手移到endpoint注册并门控普通包；[上游审查](https://lists.openwall.net/linux-kernel/2026/08/18/304)讨论入站HELLO时公告也可能被门控；[回退提案](https://lists.openwall.net/linux-kernel/2026/09/18/1409)针对其它Wi-Fi休眠回归恢复NS应答。提案/其它设备报告不等于本机验证，后续按本机直接trace修正，不盲改NV、PD映射或电压。

首次音频FWK回复116字节/token1。一次core正常重绑后首次回复与等待结果均0、API7/API2；trace phase1/phase2在245.771959/245.771961秒，但这2微秒只是完成通知至等待返回间隔，不是完整查询耗时。未运行EUD reader，未追加复测/ADSP重启。有限播放与DMIC0验证见八原包，实际声音质量未知；DMIC1/2保留104历史。

Image `{k['image_sha256']}`；DTB `{k['dtb_sha256']}`；CPIO `{k['cpio_sha256']}`。logdump `{c['logdump_sha256']}`；完整boot `{c['full_backup_boot_sha256']}` 未改写，实际FDT仅UEFI chosen允许字段不同。NV六区、persist、stock DTBO字节保留，新80块备份均SHA通过。DTB相同，无需重新构建或刷EDK2 boot。

检查点 SHA `{v['archive_sha256']}`；194文件包括八原包及全部嵌套SHA/原包逐字节核验。F1后USB消失导致reader EIO/退挂无设备，原件保留，已收F1并独立fastboot确认后才仅刷logdump。早期boot-finished/tracefs尚未出现与host读取单行bootID误取首字符的前置guard失败无设备修改，已用完整bootID重做。最初检查点以模块加载列表逐字节比较失败：早期BT辅助模块3个、用户要求stop后0个；CPIO/模块二进制仍字节相同，修正为检查该明确生命周期变化，原包不改。

## 下一轮

kernel107全新boot/PID/prefix和完整备份，优先修复HELLO未完成时NS公告丢弃，保持HELLO先行、顺序完成后公告。三段trace原件留私有目录，不能重放旧guards。首次auto1不改写为成功，当前只可称恢复后5G通过；2.4GHz/删除等待/冷启动/休眠/长稳仍待办。蓝牙不配对连接，振动无需实物反馈，NFC仅控制器。保留Android/data/GPT/NV/persist/rootfs01/F2FS/SSH/旧显示；充电收尾，不再执行旧OEM/OTP/unseal/FET/OTG/MCU/GPIO/I2C_FORCE探针；不提交推送。详见[15组状态](../linux-port/docs/HARDWARE-STATUS.md)与[最新交接](../reference/kernel106/next-session.md)。
''')
constraints=before['reference/kernel105/next-session.md'].split('MPSS用',1)[1]
constraints='MPSS用'+constraints.replace('kernel105/wpa-5g-private.conf','kernel106/wpa-5g-private.conf')
constraints=constraints.replace('DMIC0回归5.04秒非零230051、稳态208265非零/80种值/无削波；',f'DMIC0回归{m["seconds"]}秒非零{m["nonzero_samples"]}、稳态{m["steady_nonzero"]}非零/{m["steady_distinct"]}种值/无削波；')
handoff=f'''# 下一阶段：修复QRTR HELLO/服务公告顺序

当前[session106](../../sessions/{name})与[15组状态](../../linux-port/docs/HARDWARE-STATUS.md)。全硬件goal active，无预算。

{common}

当前私人kernel106/runtime-boot-id-after-private.txt绑定#105，checkpoint SHA `{v['archive_sha256']}`、194文件/八原包。next kernel107、新prefix，不能重放本轮已存在的目录、core重绑或MPSS恢复；本轮各一次，ADSP无重启。

直接证据：首轮HELLO43.999204，公告-11在43.999213，本机HELLO44.056581，公告未重试；恢复本机HELLO248.455291先行，三个公告成功，same TFTP/RMTFS PID、kernel/elf_loader及真实读写请求恢复。三个trace零丢失，原件first-radio-trace/core-rebind-once/radio-recovery-first.tar。ns.c仍未修改，只诊断；优先在HELLO与公告之间实现顺序保证/应答或可靠重试，不硬编码modem node0、不盲改NV/PD mapper/region/delay。上游HELLO v3和回退提案均在session链接，不能把提案视为已合并。

实际源码/home/cy122/x2pro-linux/linux；DTS与kernel104镜像相同，新增源码与kernel106/*.after和samurai-diag.h一致。只有CONFIG_BOOT_CONFIG_EMBED_FILE改为kernel106私有radio-bootconfig.txt，保留旧display前缀、无tp_printk。DTB/CPIO模块/原boot完全相同，本轮logdump-only；未来DTB改动必须真重建EDK2嵌入DTB。

core诊断不再同步dev_info，首次及一次正常重绑后首次100ms查询都API7/API2通过，无EUD reader/no ADSP restart。2微秒只代表phase1/phase2间隔，不能称完整耗时。旧105首次超时留历史。

{constraints}
'''
(ref/'next-session.md').write_text(handoff)
top=handoff.replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/')
for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md']:(root/n).write_text(top)
p=root/'HANDOVER-NEXT.md';s=before['HANDOVER-NEXT.md'];a=s.index('当前交接见 ');b=s.index('\n\n',a)
p.write_text(s[:a]+f'当前交接见 [阶段106](sessions/{name}) 和 [NEXT-SESSION](NEXT-SESSION.md)：Linux #105直接trace定位首轮HELLO/公告竞态；修复尚未部署，唯一恢复后5GHz通过，core首次100ms重绑查询通过。以下阶段88历史保留。'+s[b:])
(root/'DOCS-INDEX.md').write_text(before['DOCS-INDEX.md'].replace('当前：','当前：[阶段106](sessions/'+name+')、',1))
(root/'reference/kernel105/next-session.md').write_text(f'> 最新见[阶段106](../../sessions/{name})及[当前交接](../kernel106/next-session.md)。下文保留105历史；106 core首次100ms重绑查询通过，首次MPSS失败有HELLO/公告trace证据，修复尚未部署。\n\n'+before['reference/kernel105/next-session.md'])
(ref/'README.md').write_text(f'''# 阶段106：HELLO/公告竞态与音频完成后trace

[session106](../../sessions/{name})、[下一轮](next-session.md)。实际Linux #105，仅logdump；首次无线顺序缺陷有trace证据，尚未部署修复，唯一恢复后5G通过。core首次重绑100ms查询通过，无EUD reader/ADSP重启。

prepare-source/build-kernel/audit-kernel、wire-node trace修正保留原显示配置/CPIO/DTB/模块；prepare-tools/package/flash-radio使用80块全新备份、仅logdump。collect-first-radio-trace先保存启动原件，test-core-rebind-once和recover-after-mpss-crash分别保存新的独立trace且不覆盖旧原件。analyse-trace核验原包SHA/零丢失，inspect-radio-order仅协议元数据。

有限网络/播放/DMIC0回归及八原包检查点由verify-tests/verify-checkpoint校验，194文件、原包与嵌套SHA通过。update-docs/audit-public保留15组和rootfs段落。所有输出、凭据、固件、录音、原日志、镜像只在私人E:\\edk2-samurai-out\\kernel106；不提交推送，不重放旧guard目录。
''')
print('STAGE106_STATUS_AND_HELLO_ORDER_HANDOFF_UPDATED')
