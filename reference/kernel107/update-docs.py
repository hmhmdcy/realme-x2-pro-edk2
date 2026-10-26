from pathlib import Path
import json,re
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel107';out=Path('/mnt/e/edk2-samurai-out/kernel107')
v=json.loads((out/'checkpoint-validation.json').read_text());t=json.loads((out/'tests-validation.json').read_text());k=json.loads((out/'kernel-validation.json').read_text());c=json.loads((out/'candidate-validation.json').read_text());band=json.loads((out/'24g-failure-analysis.json').read_text())
assert v['checkpoint_archive_audit_pass'] and v['first_automatic_wifi_start_pass'] and v['manual_mpss_recovery_count']==0
assert band['new_connected_events']==1 and band['key_negotiation_completions']==1 and band['dhcp_lease_obtained'] and band['http_bytes']==577 and not band['wrong_key_events'] and not band['new_reason7_count']
targets=['README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md','NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','HANDOVER-NEXT.md','DOCS-INDEX.md','reference/kernel106/next-session.md']
assert not (out/'public-docs-before.json').exists()
before={n:(root/n).read_text() for n in targets};(out/'public-docs-before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2)+'\n')
name='107-qrtr-hello-reply-and-automatic-wifi-start.md';m=t['microphones'][0]
common=f'''手机已部署Linux #106（阶段107），仅刷logdump；DTB、完整boot分区、CPIO/模块、配置及显示/radio bootconfig字节保留。
QRTR恢复收到远端HELLO后先应答HELLO、再公告服务，移除会丢包返回-EAGAIN的hello_sent门控；保留endpoint初始化/MHI恢复的主动HELLO与既有重试/API。新boot首次14/64/4096三个公告成功，真实固件/RAM COW NV请求、原生PD mapper回复通过，auto worker0，无手动MPSS恢复；5GHz认证/DHCP/网关3/3/DNS/HTTP及切回5GHz复测通过。
2.4GHz单次2462MHz认证、DHCP、网关3/3和DNS通过，收到577字节HTTP内容，但wget20秒未正常退出，完整测试仍失败；本轮未见WRONG_KEY或reason7，历史reason7/删除等待及新HTTP收尾问题保留。首次自动启动已在一轮新boot验证，重复冷启动/休眠/长期稳定仍待验收。
首次音频API7/API2、2秒低音量有限播放与DMIC0回归通过，双功放start1/stop1/failed0；DMIC0 {m['seconds']}秒/{m['frames']}帧，稳态非零{m['steady_nonzero']}/{m['steady_distinct']}种值/无削波，实际声音/质量无人确认。本轮没有core重绑或ADSP重启，106阶段首次100ms重绑成功记录保留。
检查点{v['private_files_verified']}文件/七原包及所有SHA通过，首次radio trace无丢失；uptime{v['uptime_seconds']}、首次MPSS连续约{v['mpss_running_seconds']:.1f}秒，双DSP running、taint0、fatal0。本次显示超时{v['display_timeouts']}、BT phase2错误{v['bt_phase2_errors']}仍在待办；蓝牙停止不配对连接，振动standby/starts0无新脉冲，机械确认暂缓。
下一轮kernel108优先重复干净启动与2.4GHz数据/HTTP收尾，随后继续其它15组。保留Android/data/GPT/NV/persist/SSH/rootfs01/F2FS/旧显示，私人固件/日志/身份/凭据/音频/镜像不公开，不提交推送；全硬件goal active。'''
for n in ['README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md']:
    s=before[n];a=s.index('手机已部署Linux #105（阶段106）');b=s.index('全硬件goal active。',a)+len('全硬件goal active。')
    s=s[:a]+common+s[b:];s=s.replace('session106','session107',1).replace('106-first-modem-hello-race-and-core-query-tracing.md',name,1);(root/n).write_text(s)
p=root/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text()
rows={
'原生显示面板':f'历史面板/触屏记录保留；#106检查点frame-done timeout{v["display_timeouts"]}、taint0，仍待修 | 保留85–88失败快照，继续查DPU/DSI中断与休眠',
'普通USB与OTG':'CDC NCM/high-speed、系统UsbNcm/密钥SSH/SCP及EUD共存通过；新80块备份校验，完整boot不变/logdump读回通过，中断块保留并恢复传输 | OTG/外设、USB3、休眠恢复及连接重置/长期稳定性',
'Wi-Fi':'#106 HELLO应答/公告顺序修复，首次auto0且无手动modem恢复；5GHz认证/DHCP/网关3/3/DNS/HTTP通过；2.4GHz认证/DHCP/网关/DNS及577B HTTP内容通过，但wget20秒未退出，完整测试失败 | 重复启动/休眠/长期稳定；2.4GHz HTTP收尾及历史reason7/删除等待待修，不能混称本轮reason7复现',
'蓝牙':f'历史附近扫描通过；#106 phase2错误{v["bt_phase2_errors"]}，HCI为空/辅助模块正常卸载，保持停止 | 用户暂缓配对连接；保留传输错误待办',
'音频':'原生声卡/双MAX98937/WCD934x与首次API7/API2、有限播放/DMIC0非零无稳态削波回归通过；106阶段首次100ms core重绑成功记录保留 | 实际声音/拾音质量/启动瞬态/耳机/DSM/校准/休眠未验收',
'蜂窝网络/数据':'#106首轮MPSS连续running，无fatal/手动恢复，真实固件/RAM COW NV请求和PD mapper回复通过 | 通话/移动数据未验收；原NV不写，重复启动/休眠/长期稳定继续',
'振动':'AW8697原生FF/close/SIGKILL/watchdog历史电气验收保留；#106 ID97/standby/starts0/error0，无新脉冲 | 用户暂缓机械确认，按日志和静态分析推进下一项；保持唯一driver/OF身份检查'}
for label,value in rows.items():
    s,n=re.subn(r'^\| '+re.escape(label)+r' \|[^\n]+$','| '+label+' | '+value+' |',s,flags=re.M);assert n==1
s=s.replace('下一项优先QRTR HELLO/服务公告顺序与其它硬件；','下一项优先重复启动、2.4GHz数据/HTTP收尾与其它硬件；',1)
s=s.replace('同时保留首次MPSS崩溃、2.4GHz掉线、删除等待、','同时保留首次MPSS崩溃历史与新启动验收边界、2.4GHz HTTP收尾/掉线、删除等待、',1);p.write_text(s)
(root/'sessions'/name).write_text(f'''# 阶段107：QRTR HELLO应答/公告顺序修复，首次自动Wi-Fi通过

2026-10-11，实际Linux #106；全硬件目标active，尚未完成。

{common}

## 修复及实机证据

修改仅net/qrtr/af_qrtr.c和ns.c，两对象W=1零警告。根据[阶段106直接trace](106-first-modem-hello-race-and-core-query-tracing.md)，恢复NS的say_hello应答成功后才announce_servers，去掉首次普通包-EAGAIN丢弃门控及无用hello_sent标志。保留ep_lock真实xmit串行、事务流控、READ_ONCE/WRITE_ONCE、未知节点广播过滤、endpoint注册主动HELLO/100ms重试与取消生命周期、qrtr_endpoint_hello及MHI resume调用；不完整回退其它新API，不改变PD mapper、RMTFS/TFTP、固件、NV或启动delay。

[上游原改动](https://github.com/torvalds/linux/commit/544d85de4dc22c01badfd8cefa59829ce35c4858)转移HELLO所有权并删除NS应答；[回退提案](https://lists.openwall.net/linux-kernel/2026/09/18/1409)因其它Wi-Fi休眠回归恢复旧序列。本轮按本机证据做两源有限修正，保留主动初始化/resume接口，不宣称其它平台/MHI实机已验收。

新boot modem HELLO在42.873658秒进入NS，本机应答42.873677秒成功，14/64/4096公告42.873692/42.873705/42.873714秒全部0；kernel/elf_loader真实返回1 domain，随后读取固件与RAM COW NV。endpoint主动HELLO仍保留，两个DSP各有两次合法HELLO，未观察循环风暴。first-radio-trace全CPU overrun/commit-overrun/dropped均0。首次MPSS up {v['first_mpss_up_seconds']}秒，原auto worker0，检查点连续{v['mpss_running_seconds']:.3f}秒无fatal；没有手动MPSS恢复、core解绑重绑或ADSP重启。这是一轮新boot验证，不能替代重复冷启动/休眠/长期压力。

5GHz先验认证/DHCP/网关3/3/DNS/HTTP577B成功，切回5GHz再次全流程退出正常。2.4GHz2462MHz新连接/握手各1，DHCP成功、网关3/3、DNS成功，HTTP577B内容完整收到但timeout20终止wget，原result保持SINGLE_24G_ATTEMPT_FAILED，不能改判整个流程通过。新wpa日志只有主动换频reason3，没有WRONG_KEY/reason7；原件与最终5G分别保存，旧reason7仍是历史待办。下一轮结合TCP关闭/重传及HTTP响应结束边界定位，不先猜密码或NV损坏。

首次原生core API7/API2回归，阶段106非阻塞trace与100ms修复保持；本轮未重复core重绑。有限播放退出0/无错误，PCM关闭，双功放start1/stop1/failed0/global00；DMIC0偏置/MCLK On至Off、{m['seconds']}秒采样、稳态无削波。物理声音/拾音质量无人确认，历史DMIC1/2保留，振动无新脉冲，蓝牙不配对连接。

Image `{k['image_sha256']}`，DTB `{k['dtb_sha256']}`，CPIO `{k['cpio_sha256']}`；候选logdump `{c['logdump_sha256']}`，完整boot `{c['full_backup_boot_sha256']}`。两源以外全部tracked/untracked源码、配置、原bootconfig、初始文件/模块/DTB字节保持；NV六区/persist/stock DTBO和实际FDT校验通过，FDT仅UEFI chosen允许字段不同。DTB相同，只刷logdump一次，不重建/刷boot。

新80备份块中boot-040传输连接重置，未完成块保留.partial-first，校验已收块后恢复并完整拼接；设备当时双DSP running/taint0。F1回执后首次fastboot枚举未就绪，脚本在任何write前停止；新enumeration-late前缀独立确认身份/大小/候选SHA后才只写logdump。失败原件全部保留，USBipd保持Running，EUD最终detached，不forcebind未知hrdevmon。

检查点 SHA `{v['archive_sha256']}`，154文件/七原包及全部嵌套SHA/原件逐字节通过；公开15组及F2FS段落保留，凭据/身份/固件/日志/录音/镜像只在本机私有输出。不提交推送。下一輪见[交接](../reference/kernel107/next-session.md)及[15组状态](../linux-port/docs/HARDWARE-STATUS.md)。
''')
constraints=before['reference/kernel106/next-session.md'].split('MPSS用',1)[1]
constraints='MPSS用'+constraints.replace('kernel106/wpa-5g-private.conf','kernel107/wpa-5g-private.conf')
constraints=re.sub(r'DMIC0回归[^；]+；',f'DMIC0回归{m["seconds"]}秒非零{m["nonzero_samples"]}、稳态{m["steady_nonzero"]}非零/{m["steady_distinct"]}种值/无削波；',constraints,count=1)
handoff=f'''# 下一阶段：重复自动启动与2.4GHz数据/HTTP收尾

当前[session107](../../sessions/{name})和[15组状态](../../linux-port/docs/HARDWARE-STATUS.md)，全硬件goal active、无预算。

{common}

当前私人kernel107/runtime-boot-id-after-private.txt绑定实际#106，checkpoint SHA `{v['archive_sha256']}`、154文件/七原包；next kernel108/全新输出前缀，不重放旧boot/PID/guard目录。本轮无MPSS手动恢复/core重绑/ADSP restart。仅一轮新boot自动初始化成功，重复干净重启与物理冷启动仍未验收。

源码仅af_qrtr.c/ns.c改变，kernel107/*.after与实际匹配，NS HELLO先回复成功再服务公告，移除hello_sent丢包门控，主动endpoint/resume HELLO/API和流控生命周期全部保留；不是全量回退544d85d。原radio/display trace来自kernel106私有不可变bootconfig，CONFIG与106完整相同，DTB/CPIO/模块/boot不变。若未来改DTB必须真重建EDK2嵌入DTB；保留旧显示85–88，linux-port/dts旧镜像不覆盖。

优先同一#106干净重启，使用新的bootID和输出前缀/目录/guards，保留107首轮原件后验证auto0、三个公告、固件/RAM COW/5G，无须重新刷相同镜像。物理冷启动无人操作不能假称已验收。2.4GHz2462MHz认证/握手/DHCP/网关3/3/DNS及577B HTTP内容已到达，wget20秒未正常退出，测试result保持FAIL；本轮只有换频reason3，没有WRONG_KEY/reason7。当前5GHz5180已恢复并再次通过全网络流程，勿把单次HTTP结束超时等同2.4未认证或密码错误；下步先对照TCP FIN/ACK/重传和用户态wget响应长度/连接结束，历史reason7/删除等待独立保留。

{constraints}
'''
(ref/'next-session.md').write_text(handoff)
top=handoff.replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/')
for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md']:(root/n).write_text(top)
p=root/'HANDOVER-NEXT.md';s=before['HANDOVER-NEXT.md'];a=s.index('当前交接见 ');b=s.index('\n\n',a)
p.write_text(s[:a]+f'当前交接见 [阶段107](sessions/{name}) 和 [NEXT-SESSION](NEXT-SESSION.md)：Linux #106首次auto Wi-Fi通过，无手動modem恢复；5GHz全流程通过，2.4GHz认证/DHCP/网关/DNS及HTTP内容到达但进程结束超时，重复启动/长稳待验收。以下阶段88历史保留。'+s[b:])
(root/'DOCS-INDEX.md').write_text(before['DOCS-INDEX.md'].replace('当前：','当前：[阶段107](sessions/'+name+')、',1))
(root/'reference/kernel106/next-session.md').write_text(f'> 最新见[阶段107](../../sessions/{name})与[当前交接](../kernel107/next-session.md)。下文保留106失败历史，107已部署HELLO应答/公告修复并首次auto0/5G通过。\n\n'+before['reference/kernel106/next-session.md'])
(ref/'README.md').write_text(f'''# 阶段107：HELLO先应答，再公告服务

[session107](../../sessions/{name})、[下一轮](next-session.md)。实际Linux #106，仅logdump；首次auto Wi-Fi成功、5GHz全流程通过，无手动modem恢复。2.4GHz认证/DHCP/网关/DNS/577B HTTP内容通过，wget结束超时仍判完整失败。

prepare-source/build/audit只改变QRTR两源，保留主动endpoint/MHI resume API/流控、其它源码/配置/DTB/CPIO/模块/原bootconfig。prepare-tools/package/flash-radio使用80个新备份块和独立F1/fastboot guards，传输中断块和枚举早期失败原件保留，最终仅logdump一次写入。

first-radio-trace/runtime、有限auto-network/播放/DMIC0、一次24g尝试和final-network原包由verify-tests/verify-checkpoint校验；154文件/七原包/嵌套SHA通过，首次trace零丢失。analyse-band-failure保留认证成功与HTTP退出失败边界。update-docs/audit-public保留15组/F2FS段落。所有固件/日志/录音/凭据/身份/镜像私有E:\\edk2-samurai-out\\kernel107，不提交推送，不重放旧guards。
''')
print('STAGE107_AUTO_START_AND_24G_HTTP_COMPLETION_BOUNDARY_DOCUMENTED')
