from pathlib import Path
import json,re
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel103';out=Path('/mnt/e/edk2-samurai-out/kernel103')
v=json.loads((out/'checkpoint-validation.json').read_text());t=json.loads((out/'tests-validation.json').read_text());k=json.loads((out/'kernel-validation.json').read_text());c=json.loads((out/'candidate-validation.json').read_text())
assert v['checkpoint_archive_audit_pass'] and t['tests_archive_audit_pass'] and not v['microphone_signal_pass']
names=['README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md','NEXT-SESSION.md',
       'NEXT-SESSION-PROMPT.md','HANDOVER-NEXT.md','DOCS-INDEX.md','reference/kernel102/next-session.md']
assert not (out/'public-docs-before.json').exists()
before={n:(root/n).read_text() for n in names};(out/'public-docs-before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2)+'\n')
session='103-native-max98937-card-pcm-and-zero-microphone.md'
common='''手机已部署Linux #102（阶段103），原生Realme X2 Pro声卡注册，WCD934x与正确双MAX98937驱动绑定；两颗实测revision0x43。
48kHz/双通道/S16的2秒-48.16dBFS有限播放返回成功，两颗功放各start1/stop1，关闭后global00/amp80/failed0；实际扬声器声音无人确认，DSM/校准和持续大音量未验收。
48kHz单声道采样两次各241920帧/5.04秒，DMA指针前进但全部为零，麦克风尚不可用。原厂handset-mic实际DMIC0/DEC5/SLIM_TX5；当前卡缺数字mic偏置路径，先修正并验证，不能把DMA成功当录音信号通过。
原生DSP版本查询失败；只做一次正常q6core解绑/重绑，仍失败，未重启DSP，不能归因为仅缓存问题。当前两个DSP running，fatal0/taint0，显示超时2、BT phase2错误2。
本次首次MPSS/Wi-Fi自动初始化成功，5GHz认证/DHCP/DNS/HTTP、网关3/3通过；未手动恢复。原initramfs/模块不变，历史首次fatal、2.4GHz reason7/删除等待、冷启动/休眠仍开放。
240文件checkpoint/六个原包及nested清单/80块备份/boot和logdump读回/实际FDT/NV/persist不变通过；DTB已真正重建EDK2。蓝牙停止并移除、不配对连接，振动机械确认按用户要求暂缓，无新脉冲。
继续音频数字麦克风电源/路由与实际采样、APR版本响应取证，之后按15组功能推进；保留Android/data/GPT/NV/persist/SSH/旧显示及rootfs01/F2FS，所有私密固件/日志/身份/凭据/音频/二进制留本机，全硬件goal active。
'''
for name in ('README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md'):
    s=before[name];start=s.index('手机已部署Linux #101（阶段102）');endline='继续MAX98937正确驱动及声卡/DAI/播放录音接入，保留15组硬件、Android/数据/GPT/原NV/persist/SSH/显示旧快照/rootfs01与F2FS段落；全硬件goal仍active。\n'
    end=s.index(endline,start)+len(endline);s=s[:start]+common+s[end:]
    s=s.replace('session102](sessions/102-wcd934x-and-real-max98937-identification.md)',f'session103](sessions/{session})')
    s=s.replace('session102](../sessions/102-wcd934x-and-real-max98937-identification.md)',f'session103](../sessions/{session})')
    if name.endswith('HARDWARE-STATUS.md'):
        s=s.replace('2026-10-11，session102','2026-10-11，session103')
        rows={
          '原生显示面板':('历史面板/触屏等记录保留；#102当前显示frame-done timeout2、taint0，未修复','继续保留85–88失败快照，另查DPU/DSI中断与休眠'),
          'Wi-Fi':('历史双频扫描/认证/TCP哈希保留；#102首次MPSS与Wi-Fi自动初始化、5GHz认证/DHCP/DNS/HTTP/网关3/3通过，MPSS持续957秒以上','2.4GHz reason7、删除等待、首轮fatal、冷启动/休眠与长期稳定；两次近邻阶段暖启动成功不能归因音频或宣称修复'),
          '蓝牙':('历史附近扫描通过；#102两个phase2错误，当前正常stop后HCI为空；不配对连接','用户暂缓配对连接；继续保留传输错误待办'),
          '蜂窝网络/数据':('MPSS/DMS/COW基础保留；#102一次首次自动暖启动成功，未手动恢复，无新增fatal','不能当作通话/移动数据验收；原NV不写，历史首轮fatal继续'),
          '振动':('AW8697原生FF/close/SIGKILL/watchdog历史电气验收保留；#102 ID97/standby/starts0/error0，无新增脉冲','按用户要求暂缓机械确认；通过唯一driver/OF路径识别2-005a，不重放旧I2C编号'),
          '音频':('正确双MAX98937 ID43与WCD934x注册声卡；有限48k双通道PCM播放返回0且两功放关闭归零；两次单声道5.04秒DMA正常但全零；原生版本查询/一次正常core重绑仍失败','先补DMIC0/偏置1/DEC5/TX5路由，验证非零实采；记录APR实际响应；声音、麦克风质量、耳机/插拔、DSM/校准与冷启动/休眠未验收')}
        for n,(status,nextstep) in rows.items():s=re.sub(r'^\| '+re.escape(n)+r' \|.*$',f'| {n} | {status} | {nextstep} |',s,flags=re.M)
        s=s.replace('下一项继续正确MAX98937驱动、声卡/DAI与播放录音；','下一项继续数字麦克风电源/路由、非零录音及APR版本响应；')
    (root/name).write_text(s)
content=f'''# session103：MAX98937原生声卡、有限PCM与全零麦克风

2026-10-11，已真实刷入Linux #102，boot/logdump两分区及EDK2内嵌DTB读回一致。原生Realme X2 Pro声卡注册，FE播放MultiMedia1和采样MultiMedia2、QUAT_MI2S_RX与WCD934x SLIM收发后端已接入。

两颗MAX98937均读revision0x43，左右GPIO148/37由正确驱动独立拥有，空闲复位解除但global00/amp80。驱动先ID验证、无寄存器缓存、只允许核实的寄存器图，任一I2C配置错误置failed并复位，devm失败/卸载/shutdown关闭。原厂GPL MAX98937的55项表按真实enum逐地址生成，保留thermal warning75/shutdown8c/hysteresis08与brownout配置，数字44/PCM模拟1采用原厂无DSM保守值；禁止任意增益用户接口，没有OEM DSM/misc共享static实现、没有校准或NV写入。没有把MAX98927地址作偏移移植。

低级播放实测：48000Hz/stereo/S16_LE，峰值128/32768（-48.16dBFS），2秒1kHz并带渐入渐出，960帧/4period满足原生DSP对齐。tinyplay退出0/错误空，耗时{t['playback_seconds']:.2f}秒；两颗功放各starts1/stops1，关闭后global00/amp80/powered0/muted1/failed0，PCM closed。**无人在场听音，不能宣称扬声器物理声音、音质、DSM或大功率长期保护已验收。**

采样实测：AMIC1/ADC1/DEC0/TX0，以及按原厂handset-mic修正选择的DMIC0/DEC5/TX5，各录241920帧、48000Hz/mono/S16、5.04秒。live状态RUNNING，首轮hw_ptr/appl_ptr47039，period960/buffer3840；正常关闭且错误空，但两份PCM全部0，SHA `{t['microphone_dmic0']['pcm_sha256']}`。**DMA转动通过，真实麦克风信号未通过。** 原厂private mixer路径证据和官方19781音频DTS表明数字麦克风需要偏置路径；当前card仍有初始AMIC1 Handset Mic关系，缺DMIC0/1 Pin与MIC BIAS1连接。先修该缺失再实测，不能仅凭源码断言它是全零的唯一原因。私有录音不上传或公开。

原生版本查询在首次collector中报错，保留partial；retry1记录exit1/error，不能当服务API成功。当前DSP/ALSA和PCM RPC可用；只做一次普通q6core解绑/重绑（两PCM closed、功放关闭、精确service@3身份），之后查询仍失败；**无ADSP/MPSS强制崩溃或重启，未证明仅为早期缓存。** 下一轮需观察实际APR opcode/status/payload，再决定修复。

无线回归：首次自动MPSS up47.486181秒、worker结果0，本轮没有manual恢复；checkpoint uptime{v['uptime_seconds']}秒/MPSS持续{v['mpss_running_seconds']:.6f}秒。5GHz认证/DHCP/路由/DNS/577B HTTP、网关3/3通过。临时私人连接profile未内嵌。阶段102/103邻近两次暖启动成功，initramfs/无线源/固件逐字节不变，不宣称历史40秒fatal、2.4GHz reason7/删除等待、冷启动/休眠/长期稳定已修复。

蓝牙附近扫描历史保留；本轮正常stop后HCI为空，不配对连接；phase2错误2。振动ID97/standby/starts0/error0，无新播放，用户无人测试，机械确认暂缓。两个DSP running/fatal0/taint0/SMMU fault0；显示frame-done timeout2保持开放，旧85–88快照保留。

完整核验：240文件checkpoint SHA `{v['archive_sha256']}`，六个原包逐字节一致且nested manifests纳入外层清单，首个runtime/首个checkpoint partial保留；80块2MiB/8192Kbit/s完整备份和boot/logdump读回、实际FDT仅五个合法UEFI chosen字段差异、initramfs/原模块/六NV源/persist/stock DTBO保持。新增音频服务/card/pinctrl节点、正确功放compatible/vdd/channel/prefix和4个音频config变化；其它已修改源码保持。EDK2只变DTB FFS/容器，EUD/F1/compat/shim/ramdisk/执行代码保持。

Image `{k['image_sha256']}`；DTB `{k['dtb_sha256']}`；CPIO `{k['cpio_sha256']}`；boot `{c['boot_sha256']}`。

构建/调试边界：首轮默认PATH遗漏原Rust检测器，元数据变化触发guard，完整保留并恢复原PATH重建，最终仅音频config变化。canonical漏识别slim-ifc-dev导致phandle数值差异，改为校验唯一同一IFD目标，未忽略节点差异。首次tinyalsa误将-static用于shared目标失败，保留原日志，固定v2.0.0源码的静态archive/四ARM64工具通过。首次fastboot检查在F1切换时尚未枚举，没有写分区；独立确认后用新prefix刷机。postflash EUD首次attach过早失败，原生日志设置com-up后两次15秒捕获并释放，完整内核证据在NCM包中。旧tinymix省略contents命令只打印usage，旧tinypcminfo路由未启时EINVAL/错误方向ENOENT保留，实际播放/采样用明确路由与设备。首次collector在版本查询处退出，重放因目录guard停止；UUID本身有效，并非已证明熵故障。checkpoint首次假定extra模块目录失败；retry1外层find错误排除nested SHA清单，retry2只排除自身SHA清单后240文件全验。首次采样审计要求非零，真实全零触发失败；保留失败数据并明确登记信号未通过。

原厂GPL驱动参考：[固定Realme MAX98937实现](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/audio-kernel/asoc/codecs/max989xx/max98937.c)。SM8150资源/[0x1b21 strict SID](https://github.com/ClearStaff/linux-sm8150-mainline-hotdog/blob/403b56c33e2ccdda25d90378970a5e5b928dee19/arch/arm64/boot/dts/qcom/sm8150.dtsi)与同机OEM SID互证，不套SDM845 0x1821、不旁路SMMU。工具为[tinyalsa固定v2.0.0](https://github.com/tinyalsa/tinyalsa/tree/1c5fb68ced57d838f2b7ecd0c00bc1fefc9ab60d)，Android BSD许可证；二进制仅私人。

15组硬件目标继续，下一轮先数字麦克风/电源与APR响应取证。充电不重跑旧OEM/NV/OTP/unseal/FET/OTG/MCU/I2C_FORCE探针，NV仅RAM COW；Android/data/GPT/原NV/persist/SSH/rootfs01/F2FS保持。没有提交推送；固件、原DTBO/XML/库/日志、身份/凭据/录音/镜像/二进制只私人目录。
'''
(root/'sessions'/session).write_text(content)
handoff=f'''# 下一阶段：Realme X2 Pro数字麦克风与APR版本回复

当前真实部署Linux #102，逻辑阶段103，详见[session103](../../sessions/{session})和[15组状态](../../linux-port/docs/HARDWARE-STATUS.md)。全硬件goal active，无token预算，尚未完成。

原生声卡/正确双MAX98937 ID43/WCD934x与DSP服务已接入。2秒-48.16dBFS stereo/S16/48k播放退出0，双方starts1/stops1、global00/amp80/failed0，物理听音无人验证。两次mono/48k各241920帧/5.04秒DMA正常但全零，不能宣称麦克风可用；AMIC1/DEC0和原厂DMIC0/DEC5/TX5均失败。当前card缺DMIC Pin->麦克风widget->MIC BIAS1路径，原厂Digital Mic0/1用BIAS1，其它DMIC源按同机官方DTS逐项核对。先补板级电源/路由并真EDK2重建刷机、观察非零实采；若仍零，核查SLIM trigger实际返回/AFE通道与IOMMU映射，不盲目旁路或扩大mask。代码里Handset Mic目前仍AMIC1，需要修正。没有物理反馈要求的未答问题。

原生q6core版本属性读取exit1；仅一次精确service@3正常unbind/bind后仍exit1，两个DSP/声卡保持，未重启DSP。不能断言仅早期缓存。下一步记录实际APR opcode/status/length和合法payload分支，再修native查询与依赖；不能把timeout0/缺服务默认0当ready。旧#101 API7/ASM2实测保留为历史，不覆盖本轮失败。

本轮首次MPSS自动启动/worker0、5GHz认证/DHCP/网关3/3/DNS/HTTP通过，未manual恢复；相邻阶段两次暖启动成功不等于可靠性修复。原CPIO/模块/无线源码不变，历史首次40秒fatal/2.4GHz reason7/删除等待/冷启动/休眠继续。当前#102 uptime{v['uptime_seconds']}、双DSP running/fatal0/taint0/显示超时2/BT错误2；蓝牙正常stop/HCI空，不配对或连接。振动ID97/standby/starts0，无新脉冲，机械确认暂缓。

240文件checkpoint SHA `{v['archive_sha256']}`，私人E:\\edk2-samurai-out\\kernel103/checkpoint-retry2.tar，tests-validation/checkpoint-validation.json绑定六个原包。runtime完整包retry1，capture与capture-dmic0均全零；first runtime/API错误、原checkpoint模块路径错误、retry1 nested manifest缺失均保留。原UUID第一次文件只是误命名first-empty，实际有效，不要错误推断熵故障。工具脚本已有输出目录/guards，不能盲目重放。

下一轮使用kernel104/新PID与输出prefix，先重核当前真实boot ID、哈希、进程、目录与owners。旧前缀不覆盖，当前真实boot ID在私人kernel103/runtime-boot-id-after-private.txt。内核/home/cy122/x2pro-linux/linux HEAD e42788e，EDK2/home/cy122/edk2-samurai/repo HEAD f23a9f8；实际DTS对应reference/kernel103/sm8150-samurai.dts.after，linux-port/dts镜像故意保留早期状态。新源sound/soc/codecs/max98937-samurai.c及sound/soc/qcom/samurai-audio.c，四个Kconfig/Makefile改动已应用、无提交。

GPIO148/37现在由正确功放驱动拥有，空闲物理高/逻辑解除复位，但global00/amp80；不能继续用旧ID工具直接I2C_SLAVE或GPIO申请。i2c编号功放1/振动2/触摸4，MPSS用/usr/sbin/samurai-modem-remoteproc，振动按唯一driver/OF的haptics-device。QUP4 GPIO51/52、QUAT I2S137/138/139、WCD143/IRQ123已核对，GPIO54触屏保持。SMMU SID1b21 strict0、NGD1b46 strict0；不采用其它SoC/手机资源。

原factory参考固定Realme9668fcdc C/H在/home/cy122/x2pro-linux/refs/realme-amp-git-k102（无checkout、FETCH_HEAD），表55项/地址/thermal与brownout互证；固定SM8150 403b56源码在refs/sm8150-audio-k102-retry1。private kernel102/stock-audio-contract.tar包含只读同机XML；kernel103/oem-mic-contract-derived-private.json只本机。tinyalsa v2.0.0 ARM64静态四工具在私人kernel103，v2需要tinymix -D 0 contents/set/get；period要480整数倍，capture设备1。

手机仅boot/logdump刷机，DTB改变必须真EDK2重建；full80块backup和current完整readback匹配。CPIO SHA `{k['cpio_sha256']}`，Image `{k['image_sha256']}`，DTB `{k['dtb_sha256']}`，boot `{c['boot_sha256']}`。NV RAM COW仅，充电不重跑旧探针；Android/data/GPT/NV/persist/SSH/旧显示85–88/另一rootfs01全部文件及F2FS段落保留。仅自写代码/脱敏记录公开，固件/OEM XML/库/原日志/身份/密码/音频/镜像/二进制私人，不提交推送。剩余摄像头、SLPI传感器、指纹、蜂窝、GNSS等仍在全硬件目标。
'''
(ref/'next-session.md').write_text(handoff)
(root/'NEXT-SESSION.md').write_text(handoff.replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/'))
(root/'NEXT-SESSION-PROMPT.md').write_text('继续Realme X2 Pro全硬件Linux适配，先读NEXT-SESSION.md、sessions/103、reference/kernel103和私人kernel103/checkpoint-validation.json，重新核对当前boot ID/源码/镜像/进程/owners。真实Linux #102已刷boot/logdump/EDK2 DTB，正确双MAX98937 ID43与WCD声卡通过，2秒有限PCM播放退出0、功放均关闭归零；物理听音未确认。AMIC1和原厂DMIC0/DEC5/TX5各5.04秒DMA正常但全零，麦克风不通过，先补正确数字mic偏置/路由再实采，必要时跟踪SLIM trigger返回及AFE/SID，不旁路SMMU。原生版本查询及一次正常core重绑仍失败，不能仅归因早期缓存；记录真实APR回复后修，禁止强制DSP崩溃/无界恢复。首次自动无线本轮成功、5GHz认证/DHCP/DNS/HTTP/网关3/3，历史40秒fatal/2.4 reason7/删除等待/冷启动休眠保持开放。240文件checkpoint/六原包/nested SHA/80块备份/读回/实际FDT/NV/persist通过，taint0/双DSP running/fatal0/显示超时2/BT phase2错误2。BT已停止移除，不配对连接；振动无人确认，机械确认暂缓、无待答问题、不重放脉冲。下一轮kernel104新前缀，当前正确功放驱动持有GPIO37/148，不能重跑旧ID工具。保留15组目标/Android/data/GPT/NV/persist/SSH/rootfs01/F2FS/旧显示；NV RAM COW、充电旧探针不跑、只刷boot/logdump且DTB须EDK2重建。固件/OEM配置/日志/身份/凭据/音频/二进制私人，无提交推送。goal active。\n')
(ref/'README.md').write_text(f'''# kernel103：正确MAX98937/原生声卡与PCM回归

Linux #102已真实部署，双ID43/原生声卡/有限48k stereo播放和关闭归零通过；两次5.04秒录音DMA正常但全零，数字mic电源/路由仍待修；版本查询和一次core重绑仍失败。5GHz连接及网络通过，BT停止无配对，振动确认暂缓。

见[session103](../../sessions/{session})、[下一轮](next-session.md)。240文件checkpoint `{v['archive_sha256']}`，原包/nested清单/读回/FDT/NV/persist通过。这里只含自写源/脚本/补丁和脱敏说明；所有录音、原日志、原厂XML/库/固件、凭据/身份、镜像/二进制留私人目录。

guard及失败原脚本保留，实际完整runtime是retry1、checkpoint是retry2。不得盲目重放已存在目录。正确功放驱动已拥有GPIO37/148，旧kernel102 ID-only工具现在不适用。新源码/设备树已应用到WSL真实树，linux-port/dts旧镜像保持。15组硬件goal active。
''')
for name,prefix,newline in [('HANDOVER-NEXT.md','当前交接见 ',f'当前交接见 [阶段103](sessions/{session}) 与 [NEXT-SESSION](NEXT-SESSION.md)：Linux #102正确功放/声卡/有限播放通过，录音全零与版本查询仍待修；5GHz通过、BT停止。以下阶段88历史保留。'),('DOCS-INDEX.md','当前：',f'当前：[阶段103](sessions/{session})、[阶段102](sessions/102-wcd934x-and-real-max98937-identification.md)、[下一轮](NEXT-SESSION.md)。')]:
    s=before[name];line=next(l for l in s.splitlines() if l.startswith(prefix));(root/name).write_text(s.replace(line,newline))
(root/'reference/kernel102/next-session.md').write_text('当前实际状态已推进到[阶段103](../kernel103/next-session.md)：#102正确功放/原生声卡/有限PCM播放通过，录音全零与版本查询失败待修；当前5GHz可用。以下保留阶段102历史。\n\n'+before['reference/kernel102/next-session.md'])
print('AUDIO_NATIVE_CARD_AND_ZERO_SIGNAL_BOUNDARIES_RECORDED')
