from pathlib import Path
import json, re
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel104';out=Path('/mnt/e/edk2-samurai-out/kernel104')
v=json.loads((out/'checkpoint-validation.json').read_text());k=json.loads((out/'kernel-validation.json').read_text());c=json.loads((out/'candidate-validation.json').read_text())
assert v['checkpoint_archive_audit_pass'] and v['microphone_signal_pass'] and not v['native_api_query_pass']
assert v['manual_mpss_recovery_count']==1 and not v['first_automatic_wifi_start_pass']
targets=['README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md','NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','HANDOVER-NEXT.md','DOCS-INDEX.md','reference/kernel103/next-session.md']
assert not (out/'public-docs-before.json').exists()
before={n:(root/n).read_text() for n in targets}
(out/'public-docs-before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2)+'\n')
name='104-native-digital-microphones-and-first-boot-radio-failure.md'
common=f'''手机已部署Linux #103（阶段104），原生声卡/WCD934x/正确双MAX98937继续绑定，2秒-48.16dBFS有限播放返回0；功放start1/stop1、空闲global00/amp80/failed0，实际声音仍无人确认。
数字麦克风已补齐原生DMIC Pin、偏置1/3和MCLK路由。DMIC0/1/2分别5.04秒/241920帧，非零样本229767/229686/222432，SLIM启动停止均ret0，期间电源/主时钟On、结束Off；去掉前0.5秒后无满幅样本。采样通路通过，实际拾音/质量和启动瞬态仍待验。
APR三个查询包头已初始化，新增真实回复日志；首次GET_FWK/legacy都收到basic status22，未取得版本，22不是本机头文件的ENOTREADY(10)/EUNSUPPORTED(3)，含义未确认。一次正常core重绑后无回复：源代码证实APR remove删除服务IDR，而probe不重新登记，这次重试不能证明DSP持续拒绝；不再重复重绑。
首次MPSS44.773303秒up、84.759034秒fatal，39.985731秒后失败，自动worker1；先保存失败，随后一次有界恢复。恢复后5GHz认证/DHCP/DNS/HTTP和网关3/3通过，但首轮启动可靠性、2.4GHz reason7/删除等待/冷启动/休眠仍未修复。蓝牙保持停止，不配对连接；振动starts0/standby，机械确认暂缓。
{v['private_files_verified']}文件检查点/九个原包/nested SHA/80块新备份/完整boot与logdump读回/真实运行FDT/NV/persist及stock DTBO保留通过；原CPIO/模块/无线/显示源码不变，DTB真实重建EDK2。检查点uptime{v['uptime_seconds']}，双DSP running、taint0，首轮MPSS fatal1/ADSP fatal0，显示超时{v['display_timeouts']}、BT phase2错误{v['bt_phase2_errors']}。
下一轮优先首次MPSS可靠性，并修APR服务登记/版本错误处理，随后继续15组硬件与音频质量验收。保留Android/data/GPT/NV/persist/SSH/rootfs01/F2FS/旧显示，私密固件/日志/凭据/音频/二进制留本机，不提交推送；全硬件goal active。'''
for n in ['README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md']:
    s=before[n]
    start=s.index('手机已部署Linux #102（阶段103）')
    end=s.index('全硬件goal active。',start)+len('全硬件goal active。')
    s=s[:start]+common+s[end:]
    s=s.replace('session103','session104',1).replace('103-native-max98937-card-pcm-and-zero-microphone.md',name,1)
    (root/n).write_text(s)
p=root/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text()
rows={
'原生显示面板':f'历史面板/触屏记录保留；#103检查点frame-done timeout{v["display_timeouts"]}、taint0，未修复 | 保留85–88失败快照，继续查DPU/DSI中断与休眠',
'Wi-Fi':'历史双频扫描/认证/TCP哈希保留；#103首次MPSS40秒fatal、自动worker1；一次有界恢复后5GHz认证/DHCP/DNS/HTTP/网关3/3通过 | 优先首轮MPSS可靠性，2.4GHz reason7/删除等待、冷启动/休眠及长期稳定；保留失败原件',
'蓝牙':f'历史附近扫描通过；#103 phase2错误{v["bt_phase2_errors"]}，当前HCI为空且保持停止 | 用户暂缓配对连接；保留传输错误待办',
'音频':'真实声卡/双MAX98937 ID43/WCD934x，有限播放退出0；DMIC0/1/2各5.04秒非零采样，偏置/时钟正常启停；首次版本回复status22，后续core重绑丢APR登记 | 首次瞬态/实际声音/拾音质量/耳机插拔/DSM/校准/休眠未验收；修APR服务重绑登记和真实错误传播，不能将未知22当unsupported',
'蜂窝网络/数据':'MPSS/DMS/RAM COW基础保留；#103首次40秒fatal，一次有界恢复后MPSS持续running | 不能当作通话/移动数据验收；原NV不写，优先首轮可靠性',
'振动':'AW8697原生FF/close/SIGKILL/watchdog历史电气验收保留；#103 ID97/standby/starts0/error0，无新脉冲 | 用户暂缓机械确认；唯一driver/完整OF查找，不重放旧I2C编号'}
for label,text in rows.items():
    pattern=r'^\| '+re.escape(label)+r' \|[^\n]+$'
    s,count=re.subn(pattern,'| '+label+' | '+text+' |',s,flags=re.M);assert count==1,label
s=s.replace('下一项继续数字麦克风电源/路由、非零录音及APR版本响应；','下一项优先首次MPSS启动可靠性、APR登记/查询错误处理与音频质量；',1)
p.write_text(s)
session=f'''# 阶段104：数字麦克风恢复采样，首次无线崩溃仍待修

2026-10-11，真实Linux #103已刷boot/logdump；全硬件目标继续，未完成。用户蓝牙不配对连接、振动机械确认暂缓、NFC只验证控制器。

{common}

## 修改与来源

同机原厂[19781音频拓扑](https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2Pro-kernel-source/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/19781/sm8150-oppo-audio-overlay.dtsi)与只读本机mixer_paths私有归档互证：handset走DMIC0/DEC5/TX5，第二路DMIC1/DEC7/TX7，speaker-mic中DMIC2用偏置3。原生WCD934x把输入Pin与DMIC ADC分开，必须补DMIC Pin至麦克风widget、DMIC至偏置供电及MCLK；电压/时钟保持原厂1.8V/9.6MHz。只新增三路已核对的输入，不移植原厂整个拓扑。

三个q6core栈上APR包完整初始化，原apr_send_pkt仅填domain/service，不能留下任意port/token。增加本机有限速率的opcode/payload长度/port/token/basic status与合法版本条目计数日志。WCD SLIM trigger传播prepare/enable/disable/unprepare错误，enable失败时正常回收准备状态。没有新增绕过SMMU、直接I2C或GPIO探针，也未修改功放增益。

初始版本查询在18.512秒发送20字节、port0/token0，FWK与legacy都有8字节basic回复、status22，均无合法版本条目。22在同机GPL头文件中是ADSP_ERR_MAX边界，不等于ENOTREADY=10或EUNSUPPORTED=3，当前固件含义未知。254.218638秒唯一core重绑后只有send、没有reply；静态核对drivers/soc/qcom/apr.c发现apr_device_remove从svcs_idr删除服务，而apr_device_probe不回填。这个重试本身破坏回复路由，不能将其当作“缓存不是原因”或“DSP持续拒绝”的证据。AFE/ASM/ADM仍登记，播放录音通过；ADSP未重启。下一轮必须先修登记生命周期，再修缓存/超时/basic错误语义，不能反复重绑。

## 实机验收

| 路径 | 帧/时长 | 非零样本 | 去掉首0.5秒后的范围/RMS | 电源/传输 |
|---|---|---|---|---|
| DMIC0/DEC5/TX5 | 241920/5.04秒 | 229767 | -45至38 / 8.783648 | MIC BIAS1/MCLK On；SLIM启停0；结束Off |
| DMIC1/DEC7/TX7 | 241920/5.04秒 | 229686 | -37至39 / 8.662093 | MIC BIAS1/MCLK On；SLIM启停0；结束Off |
| DMIC2/DEC5/TX5 | 241920/5.04秒 | 222432 | -24至22 / 4.937010 | MIC BIAS3/MCLK On；SLIM启停0；结束Off |

均48kHz/mono/S16、960帧×4 period，DMA live RUNNING，exit0/空stderr；每路只有对应DMIC开启，结束PCM closed。最初0.5秒内有满幅瞬态，后段满幅0；尚无已知声源响应/人声质量/物理声音确认，不能宣称完整音频验收。录音原件仅私有目录，不公开播放。

2秒双通道低幅自生成测试音重测通过；双功放start1/stop1，global00/amp80/failed0，未做DSM、校准、持续大音量或耳机测试。

首次MPSS up44.773303、fatal84.759034（差39.985731秒），自动无线worker1；九包保留首次runtime、first-boot-failure与原无线/蓝牙/QRTR/只读服务日志。仅一次手动stop/start MPSS，原tftp/rmtfs服务PID及命令行验证、NV RAM COW保持；ADSP唯一完整OF与真实firmware路径核对。原boot-finished=1不改。恢复后5GHz5180认证/DHCP/网关3发3收/DNS/577字节HTTP通过，蓝牙未启动。

## 构建、部署与完整性

配置不变，W=1两处C目标无警告，DT仅原来两个addr-size警告；只改samurai DTS、q6core、WCD934x，其它tracked/untracked源和initramfs文件/模块保持。Image `{k['image_sha256']}`，DTB `{k['dtb_sha256']}`，CPIO `{k['cpio_sha256']}`。真实EDK2 DTB FFS/container变化，其他可执行字节/shim/compat/ramdisk/EUD/F1来源不变。

新80×2MiB备份全SHA通过，原boot full `{c['full_backup_boot_sha256']}`、logdump `{c['full_backup_logdump_sha256']}`。仅两分区flash，boot {c['boot_bytes']}字节 `{c['boot_sha256']}`，logdump `{c['logdump_sha256']}`；完整读回、运行FDT仅合法UEFI chosen差异、六NV/persist/stock DTBO及部署服务/模块哈希通过。

检查点九个原包逐字节及嵌套manifest绑定，共{v['private_files_verified']}个文件，SHA `{v['archive_sha256']}`，uptime{v['uptime_seconds']}、恢复MPSS持续{v['mpss_running_seconds']}秒。所有原日志/固件/OEM XML/录音/身份/凭据/镜像在私人kernel104；公共目录仅自写/修改GPL代码、脚本与脱敏记录。usbipd保持Running，EUD detached，自有宿主helpers为0。

## 保留的失败与下一步

首编译日志的payload长度格式警告与镜像全部保留first-format后修复；split工具旧#101 guard在创建分块前阻止运行，改#102后新分块；恢复工具首次ADSP firmware路径guard拒绝、未创建恢复目录，核对实际qcom/sm8150/realme/samurai/adsp.mdt后才唯一恢复。F1 receipt后设备消失EIO是重启边界，已finally释放USB；未知hrdevmon提示保留，没有force-bind。所有guard/错误原件私人保存，不替换成成功记录。

优先获取首次MPSS40秒崩溃的有限SMEM/QRTR/rmtfs请求链证据，不盲增delay或循环DSP恢复；5GHz只有一次恢复后的有限联网通过。2.4GHz reason7、删除等待、冷启动/休眠、显示超时、BT传输、USB稳定性继续。音频采样已前进，但已知声源/首次瞬态、耳机插拔、版本服务登记仍需修验。摄像头、SLPI传感器、指纹、蜂窝、GNSS等仍在15组目标内。
'''
assert not (root/'sessions'/name).exists();(root/'sessions'/name).write_text(session)
handoff=f'''# 下一阶段：优先首次MPSS可靠性，修APR登记并继续音频验收

当前真实Linux #103/逻辑阶段104，详见[session104](../../sessions/{name})和[15组状态](../../linux-port/docs/HARDWARE-STATUS.md)。全硬件goal active，无token预算，尚未完成。

{common}

下一轮kernel105/全新PID与输出prefix，先核对实机boot ID、实际源码/镜像/进程/owner，不重放已有guard目录。私人kernel104/runtime-boot-id-after-private.txt是真实当前boot ID；checkpoint.tar SHA `{v['archive_sha256']}`，tests-validation/checkpoint-validation.json绑定九个原包及{v['private_files_verified']}文件。

优先首次MPSS40秒fatal，自动boot-finished1与first-boot-failure完整保留，一次恢复后当前5GHz通过；首次up44.773303/fatal84.759034，恢复up313.3625，检查点uptime{v['uptime_seconds']}。采集SMEM reason返回值/长度及请求链证据，不能无界恢复或只延长固定delay。NV RAM COW、原NV/persist不写；当前服务tftp/rmtfs自有PID守卫，不能重复启动它们。

APR查询当前不能可信恢复：初始FWK/legacy各basic status22，22含义未确认，与ENOTREADY10/EUNSUPPORTED3不同；一次core解绑重绑从svcs_idr删服务但probe不回填，随后没有reply。因此不能用这次重绑作为有效重试，更不能再反复重绑。先修drivers/soc/qcom/apr.c正常driver生命周期登记（严格同svc指针/ID、加锁与失败回收），再记录真实opcode/header/domain/service/status、修缓存仅合法版本成功与超时/未知basic错误传播。当前AFE/ASM/ADM仍绑定，未重启ADSP；不要强制DSP crash。旧#101真实API7/ASM2只保留历史。

数字DMIC0/1/2板级bias/MCLK已补，三个5.04秒非零采样通过、SLIM启停ret0、结束Off；最初0.5秒存在满幅瞬态，后段0满幅，实际已知声源/人声质量待验。当前Handset Mic已是DMIC0，不再按AMIC1采。路由DMIC0/DEC5/TX5、DMIC1/DEC7/TX7、DMIC2/DEC5/TX5，开各自Handset/Secondary/Speaker Mic Switch；960帧×4 period，capture card0/device1。私人四个tinyalsa v2.0.0静态工具kernel104，tinymix -D 0 contents/set/get；物理扬声器声音仍未确认，2秒-48.16dBFS有限播放各功放start1stop1/global00/amp80。

实际内核/home/cy122/x2pro-linux/linux HEAD e42788e，EDK2/home/cy122/edk2-samurai/repo HEAD f23a9f8。当前DTS对应reference/kernel104/sm8150-samurai.dts.after，native q6core/WCD sources对应q6core.c.after/wcd934x.c.after；正确MAX98937和samurai machine源保持kernel103版本。linux-port/dts早期镜像故意不覆盖。当前CPIO `{k['cpio_sha256']}`、Image `{k['image_sha256']}`、DTB `{k['dtb_sha256']}`、boot `{c['boot_sha256']}`；配置/模块不变。

MPSS用/usr/sbin/samurai-modem-remoteproc，ADSP真实固件qcom/sm8150/realme/samurai/adsp.mdt、完整OF remoteproc@17300000；不能凭remoteproc编号。amps1-0039/1-003a，motor2-005a，touch4-0020；haptics helper唯一driver/89c000完整OF。GPIO148/37归功放驱动，空闲物理高解除复位但global00；不重跑旧I2C/GPIO ID工具。WCD143/QUP4 GPIO51/52/QUAT137–139/触屏54保持，SID1b21 strict0/NGD1b46 strict0，不旁路SMMU。

固定原厂9668fcdc/19781拓扑与同机private mixer XML互证；已知DMIC0/1 BIAS1、DMIC2 BIAS3，未移植全部其它DMIC。OEMAPR/GPL q6core参考在私人kernel104/oem-*.{ 'c/h/dtsi' }，公共来源链接见session。首次failed guard/格式警告/错误路径均保留，不能据host报错误判新boot ID/熵或整机panic。

下次完整boot/logdump新备份、实际EDK2 DTB重建、F1后独立fastboot/分区大小/源SHA审计，只刷boot/logdump。保留Android/data/userdata/GPT/NV/persist/SSH/显示85–88/rootfs01所有文件和F2FS段落。充电收尾，不重跑OEM充电/NV/OTP/unseal/FET/OTG/MCU/I2C_FORCE探针。蓝牙停止、不配对连接；振动机械确认暂缓、不重放脉冲；NFC无标签只控制器。固件/原日志/配置/身份/凭据/音频/镜像/二进制私人、不提交推送。摄像头/传感器/指纹/蜂窝/GNSS及所有15组功能仍需推进。
'''
(ref/'next-session.md').write_text(handoff)
assert before['NEXT-SESSION.md']==(root/'reference/kernel103/next-session.md').read_text().replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/')
(root/'NEXT-SESSION.md').write_text(handoff.replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/'))
(root/'NEXT-SESSION-PROMPT.md').write_text('继续Realme X2 Pro全硬件Linux适配。先读NEXT-SESSION.md、sessions/104、reference/kernel104和私人kernel104/checkpoint-validation.json；重新核对当前#103实机boot ID/源码/镜像/进程/owners。优先首次MPSS40秒fatal与无线可靠性：本次auto失败，唯一有界恢复后5GHz认证/DHCP/DNS/HTTP/网关3/3通过，原worker1及失败记录不改，NV仅RAM COW，不盲增delay/循环重启。数字DMIC0/1/2各5.04秒非零采样、偏置/MCLK和SLIM启停通过；首0.5秒瞬态与已知声源/真实声音/人声质量仍待验。APR包头初始化后首次FWK/legacy收到未知status22，不能当ENOTREADY10/EUNSUPPORTED3；core一次重绑删除IDR而probe不回填，后续无回复不是有效重试。先修APR正常生命周期登记/真实错误与缓存，再验证版本，禁止强制ADSP crash。174文件九原包/nested SHA/80块备份/完整读回/FDT/NV/persist/stockDTBO通过；checkpoint双DSP running/taint0、MPSS首轮fatal1/ADSP0、显示3/BT1。蓝牙保持停止不配对连接，振动机械确认暂缓不重放。新kernel105/prefix、真实EDK2 DTB重建、仅boot/logdump；保留15组目标/Android/data/userdata/GPT/NV/persist/SSH/rootfs01/F2FS/旧显示，充电旧探针不跑。私有固件/日志/配置/身份/凭据/录音/镜像留本机、不提交推送；goal active。\n')
p=root/'HANDOVER-NEXT.md';s=before['HANDOVER-NEXT.md'];a=s.index('当前交接见 ');b=s.index('\n\n',a)
p.write_text(s[:a]+f'当前交接见 [阶段104](sessions/{name}) 与 [NEXT-SESSION](NEXT-SESSION.md)：Linux #103三个数字mic恢复非零采样；首轮MPSS40秒fatal，唯一恢复后5GHz通过；APR status22与重绑登记缺失待修。以下阶段88历史保留。'+s[b:])
p=root/'DOCS-INDEX.md';s=before['DOCS-INDEX.md'];s=s.replace('当前：[阶段103]',f'当前：[阶段104](sessions/{name})、[阶段103]',1);p.write_text(s)
p=root/'reference/kernel103/next-session.md';p.write_text(f'> 当前后续见 [阶段104](../../sessions/{name}) 和 [最新交接](../kernel104/next-session.md)。下文保留阶段103历史；其core重绑重试解释已由阶段104的APR IDR源码审计补充。\n\n'+before['reference/kernel103/next-session.md'])
(ref/'README.md').write_text(f'''# 阶段104：三个数字麦克风原生采样

当前[session104](../../sessions/{name})、[下一轮](next-session.md)。Linux #103真实刷机，三个DMIC恢复非零采样；首次MPSS失败后唯一恢复5GHz通过，APR版本与正常重绑登记缺失仍待修，全硬件目标未完成。

| 工具 | 用途 |
|---|---|
| prepare-source.py、build-audio.sh、audit-kernel.py | 同机DMIC供电/时钟、APR包头/回复日志、SLIM真实错误及保留审计 |
| repair-build-format.py | 保存首次格式警告结果与旧split guard，修正后重建，不能重放 |
| prepare-deploy.py、build-firmware.sh、verify-firmware.py | 全新部署工具和真EDK2 DTB FFS校验 |
| collect-preflash.sh、split-backups.sh、receive-backups.ps1、prepare-package.py | 新80块备份、原包SHA、候选FAT/身份/凭据排除审计 |
| stop-connectivity.sh、reboot-f1.ps1、flash-audio.ps1、read-eud.ps1 | 受控停止、F1 receipt、独立枚举后仅boot/logdump、finally释放 |
| prepare-tests.py、collect-audio-runtime.sh、test-capture-dmic.sh、test-playback.sh | fresh boot/真实读回，有限三mic采样与DAPM状态/低幅播放 |
| collect-boot-failure.sh、recover-after-mpss-crash.sh、test-auto-network.sh | 保存auto1/fatal后唯一有界恢复/5GHz验证，BT保持停止 |
| test-core-rebind-once.sh | 本次已执行、保留无回复；APR IDR缺陷已确认，勿重复作为重试 |
| verify-tests.py、collect-checkpoint.sh、verify-checkpoint.py | 九原包/全部nested manifest/{v['private_files_verified']}文件与硬件边界校验 |

所有脚本有旧目录/启动/身份守卫，不能盲重放；私人输出在E:\\edk2-samurai-out\\kernel104，录音/原日志/镜像/固件/OEM XML/身份/凭据不公开。仅自写与修改GPL代码、脱敏记录公开，不提交推送。
''')
print('STAGE104_PUBLIC_STATUS_AND_FULL_GOAL_HANDOFF_UPDATED')
