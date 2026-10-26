from pathlib import Path
import json,re
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel105';out=Path('/mnt/e/edk2-samurai-out/kernel105')
v=json.loads((out/'checkpoint-validation.json').read_text());t=json.loads((out/'tests-validation.json').read_text());k=json.loads((out/'kernel-validation.json').read_text());c=json.loads((out/'candidate-validation.json').read_text())
assert v['checkpoint_archive_audit_pass'] and t['native_api_query_pass'] and not v['first_automatic_wifi_start_pass']
targets=['README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md','NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','HANDOVER-NEXT.md','DOCS-INDEX.md','reference/kernel104/next-session.md']
assert not (out/'public-docs-before.json').exists()
before={n:(root/n).read_text() for n in targets}
(out/'public-docs-before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2)+'\n')
name='105-apr-rebind-and-first-modem-crash-smem-diagnostics.md'
common=f'''手机已部署Linux #104（阶段105），本轮仅刷logdump；DTB、整个boot分区、原CPIO/模块/无线/显示源码保留。
APR服务登记移至每次driver probe，解绑先移除登记并等待在途APR回调；修正包头长度边界。core查询使用非零事务token，只接受匹配回复，合法版本成功才缓存，未知basic错误不当unsupported，超时明确返回。首次原生回复AFE API7/ASM API2；一次正常core重绑后收到合法回复，第一次100ms查询仍超时，EUD读取期间一次有界复测通过，超时原件保留。
首次MPSS约40秒fatal仍未修复：SMEM421全局/调制解调器私有区均返回-ENOENT，崩溃原因项不存在。首轮没有来自modem的TFTP/RMTFS读写请求，原worker1与失败完整保留；唯一手动恢复后，同一组RAM COW服务收到真实请求，5GHz认证/DHCP/DNS/HTTP/网关3/3通过。
2秒-48.16dBFS有限播放回归退出0、双功放start1/stop1/failed0；DMIC0回归5.04秒/241920帧，非零230051，稳态208265非零/80种值/0削波，偏置和MCLK正常关闭；历史三路DMIC采样保留，实际声音和拾音质量仍无人确认。蓝牙保持停止、不配对连接；振动standby/starts0，无新脉冲，机械确认暂缓。
{v['private_files_verified']}文件检查点/八原包及全部SHA、新80块备份、完整分区读回与实际FDT/NV/persist/stock DTBO保留通过。检查点uptime{v['uptime_seconds']}、恢复MPSS连续约{v['mpss_running_seconds']:.1f}秒，双DSP running、taint0，历史首轮MPSS fatal1/ADSP0、显示超时{v['display_timeouts']}、BT phase2错误{v['bt_phase2_errors']}。
下一轮优先首次MPSS启动的QRTR/GLINK/原生PD mapper请求链，检查core诊断日志与100ms时限相互影响，随后继续15组硬件。保留Android/data/GPT/NV/persist/SSH/rootfs01/F2FS/旧显示，固件/日志/身份/凭据/音频/镜像留本机，不提交推送；全硬件goal active。'''
for n in ['README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md']:
    s=before[n];a=s.index('手机已部署Linux #103（阶段104）');b=s.index('全硬件goal active。',a)+len('全硬件goal active。')
    s=s[:a]+common+s[b:]
    s=s.replace('session104','session105',1).replace('104-native-digital-microphones-and-first-boot-radio-failure.md',name,1)
    (root/n).write_text(s)
p=root/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text()
rows={
'原生显示面板':f'历史面板/触屏记录保留；#104检查点frame-done timeout{v["display_timeouts"]}、taint0，未修复 | 保留85–88失败快照，继续查DPU/DSI中断与休眠',
'普通USB与OTG':'CDC NCM/high-speed、系统UsbNcm/密钥SSH/SCP及EUD共存已实测；本轮80个新备份块SHA通过，boot完整不变、logdump完整读回相符 | OTG/外设、USB3、休眠恢复和长期稳定性',
'Wi-Fi':'历史双频扫描/认证/TCP哈希保留；#104首次MPSS约40秒fatal、auto worker1，SMEM421返回ENOENT；唯一恢复后5GHz认证/DHCP/DNS/HTTP/网关3/3通过 | 优先首次QRTR/GLINK/PD mapper请求链；2.4GHz reason7/删除等待/冷启动/休眠/长期稳定仍待修',
'蓝牙':f'历史附近扫描通过；#104 phase2错误{v["bt_phase2_errors"]}，当前HCI为空且保持停止 | 用户暂缓配对连接；保留传输错误待办',
'音频':'原生声卡/双MAX98937/WCD934x及有限播放回归通过；DMIC0回归非零无稳态削波，历史三路采样保留；首次AFE API7/ASM API2与重绑后有界复测通过，第一次100ms超时原件保留 | 实际声音/拾音质量/启动瞬态/耳机/DSM/校准/休眠未验收；检查诊断日志阻塞与查询时限，不将有回复等同首次查询成功',
'蜂窝网络/数据':'MPSS/RAM COW基础保留；#104首次约40秒fatal，唯一恢复后持续running，崩溃原因SMEM项缺失 | 通话/移动数据未验收；原NV不写，优先首次启动可靠性',
'振动':'AW8697原生FF/close/SIGKILL/watchdog历史电气验收保留；#104 ID97/standby/starts0/error0，无新脉冲 | 用户暂缓机械确认，按日志和静态分析推进下一项；保持唯一driver/OF身份检查'}
for label,value in rows.items():
    s,n=re.subn(r'^\| '+re.escape(label)+r' \|[^\n]+$','| '+label+' | '+value+' |',s,flags=re.M);assert n==1
s=s.replace('下一项优先首次MPSS启动可靠性、APR登记/查询错误处理与音频质量；','下一项优先首次MPSS请求链、APR查询日志/时限与其它硬件；',1);p.write_text(s)
(root/'sessions'/name).write_text(f'''# 阶段105：APR重绑登记恢复，首次MPSS无崩溃原因项

2026-10-11，Linux #104真实部署；全硬件目标继续，尚未完成。

{common}

## 源码与验证

修改仅drivers/soc/qcom/apr.c、drivers/remoteproc/qcom_q6v5.c和sound/soc/qcom/qdsp6/q6core.c；三个对象W=1零警告。APR登记原本只在device创建时发生，driver remove删除后probe不回填。本轮改为probe登记、严格ID/同指针冲突检查及失败回收；APR路径使用SRCU等待在途回调后释放，长度验证包含可选头边界。GPR动态端口生命周期未作完整验收，不宣称其它平台已测试。

core命令/事务token匹配，basic EOK只作ack，显式EUNSUPPORTED才fallback；其它错误返回EIO，合法版本表才缓存，超时ETIMEDOUT，不再假成功。新boot首次FWK回复116字节，token1；正常重绑后登记和回复恢复，第一次sysfs查询超时，一次EUD读取期间复测返回API7/API2。日志输出导致响应处理超过100ms是待证解释，本轮没有用永久延长delay掩盖问题，未重启ADSP。

真实fatal IRQ只读SMEM，记录返回值/长度及ready/handover状态，字符串最多4096字节且不写SMEM。全局和modem-host1的421都ENOENT，不能将其解释为已取得DSP错误。原厂同机[remoteproc源码](https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2Pro-kernel-source/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/remoteproc/qcom_q6v5_pil.c)也使用全局项；本轮只增加有限读取诊断。

[上游tqftpserv](https://github.com/linux-msm/tqftpserv)支持临时readwrite探测；本机既有server_check RAM支持及SM8150原生PD mapper映射已存在。首轮失败没有modem文件请求，恢复后同一组服务收到server_check、wlanmdsp及RMTFS请求，尚无证据支持改NV或扩大持久写权限。

Image SHA `{k['image_sha256']}`；DTB/CPIO分别`{k['dtb_sha256']}`/`{k['cpio_sha256']}`，字节保持。候选logdump SHA `{c['logdump_sha256']}`；完整boot保持 `{c['full_backup_boot_sha256']}`。DTB没有变化，因此复用阶段104已校验的真实嵌入DTB，未重建或刷boot。仅logdump一次写入，F1后独立fastboot确认身份/大小/候选SHA；NV/persist/stock DTBO不变。

八原包包含初始runtime、一次core重绑、有界core复测、有限播放/DMIC0、首轮失败、一次恢复及5GHz测试。检查点 SHA `{v['archive_sha256']}`，149文件/全部嵌套SHA及原包逐字节匹配。早期SSH未就绪与候选首次运行时备份尚未拼接的失败均未触发刷机；原失败记录保留。SRCU错误退出路径已在刷机前静态修正并重新构建。

## 后续

首次MPSS自up {v['first_mpss_up_seconds']}至fatal诊断{v['first_mpss_fatal_seconds']}，约40秒，auto1保留。下一轮按优先级采集原生PD mapper请求/回复与QRTR/GLINK启动事件，比较失败和唯一恢复，不能无界重启DSP、强制crash或猜测NV内容。检查core诊断输出在事务完成前阻塞的可能性。2.4GHz reason7、删除等待、显示超时、BT传输、冷启动/休眠等仍在待办。

用户无需补充振动物理反馈；蓝牙不配对连接，NFC无标签仅控制器。音频实际声音/质量、耳机/DSM/校准未确认。充电收尾，不重放OEM充电/OTP/unseal/FET/OTG/MCU/GPIO/I2C_FORCE探针。保留rootfs01/F2FS和Android全部数据，不提交推送。详见[15组状态](../linux-port/docs/HARDWARE-STATUS.md)和[下一轮](../reference/kernel105/next-session.md)。
''')
handoff=f'''# 下一阶段：优先首次MPSS请求链与APR日志时限

当前[session105](../../sessions/{name})与[15组状态](../../linux-port/docs/HARDWARE-STATUS.md)。全硬件goal active，无预算、尚未完成。

{common}

下一轮kernel106/全新输出前缀；当前私人kernel105/runtime-boot-id-after-private.txt及checkpoint SHA `{v['archive_sha256']}`绑定真实#104。八原包全部校验，tests/checkpoint-validation.json有149文件、第一次core重绑超时及后续成功边界。只执行一次core重绑、一次MPSS恢复，ADSP无重启。

首次WiFi失败没有modem TFTP/RMTFS请求；SMEM421全局/host1 ENOENT，不能称已取得fatal原因。原生SM8150 PD mapper映射、server_check RAM支持既有，勿盲复制其它机型region/永久PD电压floor或延长delay。下步补board-only、有限的PD mapper请求/回复、QRTR/GLINK事件并比较首轮/恢复；必须保存原auto worker1，只有有界恢复能作为当前5G证据，2.4GHz reason7仍未修复。

APR初始FWK116字节/API7/API2通过，driver正常重绑后登记与packet回复恢复，但第一次100ms sysfs读取超时；EUD reader期间一次有界复测通过。检查q6core callback在complete之前的诊断输出可能阻塞，优先将诊断置于完成之后或用不阻塞的trace；这是待证解释。不要把status22说成ENOTREADY或unsupported，当前缓存只存合法版本，命令/token严格匹配。无需重复重绑或ADSP restart。

当前实际源码/home/cy122/x2pro-linux/linux；DTS与reference/kernel104/sm8150-samurai.dts.after一致，新增三C源与kernel105/*.c.after一致。DTB/CPIO相同、完整boot未刷，本轮只logdump；未来若改DTB必须真重建EDK2嵌入DTB。配置/旧源码/模块/所有旧显示快照保持，linux-port/dts旧镜像故意不覆盖。

MPSS用/usr/sbin/samurai-modem-remoteproc完整OF与固件定位，不固定remoteproc编号；ADSP qcom/sm8150/realme/samurai/adsp.mdt。amps1-0039/1-003a归驱动，GPIO148/37不要重新直接操控；WCD143、QUP4 GPIO51/52、QUAT137–139和触屏54保持。motor唯一driver/89c000 OF，现2-005a starts0无新脉冲。5G私有配置kernel105/wpa-5g-private.conf限制5180，不要用kernel95的2462配置。

DMIC0回归5.04秒非零230051、稳态208265非零/80种值/无削波；DMIC1/2保留104历史。两个PCM关闭，功放global00/amp80/start1stop1failed0；实际声音/已知声源质量无人确认，勿称完整音频可用。振动按用户日志/静态分析推进，不提问/不重放脉冲；BT保持停止不配对连接；NFC仅控制器。

保留Android/data/userdata/GPT/NV/persist/SSH/rootfs01/F2FS/显示85–88所有内容。只刷boot/logdump，DTB不变优先logdump；每轮全新完整两分区备份。NV RAM COW，不持久写。充电收尾不再执行旧OEM/NV/OTP/unseal/FET/OTG/MCU/GPIO/I2C_FORCE探针。所有固件/原日志/身份/凭据/音频/镜像私人，公开仅自写/GPL修改与脱敏记录，不提交推送。USBipd保持Running，EUD最终detached，hrdevmon警告保留、不forcebind。继续15组硬件优先无线可靠性。
'''
(ref/'next-session.md').write_text(handoff)
top=handoff.replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/')
for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md']:(root/n).write_text(top)
p=root/'HANDOVER-NEXT.md';s=before['HANDOVER-NEXT.md'];a=s.index('当前交接见 ');b=s.index('\n\n',a)
p.write_text(s[:a]+f'当前交接见 [阶段105](sessions/{name}) 和 [NEXT-SESSION](NEXT-SESSION.md)：Linux #104 APR登记/原生API回复恢复；首轮MPSS约40秒fatal仍待修，唯一恢复后5GHz及音频回归通过。以下阶段88历史保留。'+s[b:])
p=root/'DOCS-INDEX.md';p.write_text(before['DOCS-INDEX.md'].replace('当前：','当前：[阶段105](sessions/'+name+')、',1))
(root/'reference/kernel104/next-session.md').write_text(f'> 当前后续见[阶段105](../../sessions/{name})与[最新交接](../kernel105/next-session.md)。下文保留104历史，APR登记已由105修复，首轮MPSS失败仍保留。\n\n'+before['reference/kernel104/next-session.md'])
(ref/'README.md').write_text(f'''# 阶段105：APR登记与首次MPSS诊断

[session105](../../sessions/{name})、[下一轮](next-session.md)。真实Linux #104，仅刷logdump；APR登记/API恢复，首次MPSS约40秒fatal仍未修，唯一恢复后5G和有限音频回归通过。

prepare-source/build-kernel/audit-kernel用于三C源及保留校验；add-private-smem-diagnostic和repair-srcu-error-cleanup是刷机前修正，guard不能重放。prepare-tools/package与flash-radio仅logdump，80块完整备份及F1独立枚举审计。

collect-audio-runtime/test-core-rebind-once与core-followup原件保留第一次100ms超时及EUD读取期间复测成功；first-boot-failure/recover-after-mpss-crash/test-auto-network保留auto1和唯一恢复。test-playback/test-capture-dmic仅有限低音量/DMIC0回归，无振动脉冲/BT配对。collect/verify-checkpoint绑定八原包及149文件，update-docs/audit-public保留15组与rootfs段落。

输出、固件、录音、凭据、日志、镜像均在私人E:\\edk2-samurai-out\\kernel105；仅源码/脚本/脱敏文档公开，不提交推送。所有boot/PID/prefix/旧目录守卫必须保留，不重放现有输出。
''')
print('STAGE105_STATUS_AND_HANDOFF_UPDATED_WITH_FIRST_BOOT_FAILURE_BOUNDARY')
