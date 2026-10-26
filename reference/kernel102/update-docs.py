from pathlib import Path
import json,re,tarfile
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel102';out=Path('/mnt/e/edk2-samurai-out/kernel102')
check=json.loads((out/'checkpoint-validation.json').read_text())
assert check['checkpoint_archive_audit_pass'] and check['actual_amp_model']=='MAX98937'
names=['README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md','NEXT-SESSION.md',
 'NEXT-SESSION-PROMPT.md','HANDOVER-NEXT.md','DOCS-INDEX.md','reference/kernel101/next-session.md']
assert not (out/'public-docs-before.json').exists()
before={n:(root/n).read_text() for n in names}
(out/'public-docs-before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2)+'\n')
session='102-wcd934x-and-real-max98937-identification.md'
common='''手机已部署Linux #101（阶段102），WCD934x真实芯片ID 0x108/0x1、SLIMbus与codec绑定通过，ADSP原生回复AFE API7/ASM API2；ALSA尚无声卡。
左右功放实测为MAX98937，地址0x39/0x3a，0x0600均返回0x43；原厂max98927L/R名称不能直接套主线MAX98927。错误组件已解绑、GPIO148/37保持物理低复位；未写功放寄存器数据、未播放。
本次首次MPSS自动启动与Wi-Fi初始化成功，5GHz认证/DHCP/DNS/HTTP、网关3/3通过；未手动恢复MPSS。仅一次暖启动，历史首轮40秒fatal、2.4GHz reason7及删除等待仍待修复。
125文件checkpoint/原包与nested清单/80块完整备份/boot与logdump读回/6NV与persist不变通过；两个DSP running、taint0，本轮显示超时2、BT phase2错误2。
蓝牙控制器已关闭并移除，不配对连接；用户暂缓振动机械确认，当前ID97/standby/starts0/error0，无新增振动播放。
DTB改变已真正重建EDK2；initramfs、已有模块与其它内核源码保持。新增QUP4使I2C编号变化，振动改按唯一驱动/DT路径解析，不重放旧编号脚本。
继续MAX98937正确驱动及声卡/DAI/播放录音接入，保留15组硬件、Android/数据/GPT/原NV/persist/SSH/显示旧快照/rootfs01与F2FS段落；全硬件goal仍active。
'''
for name in ('README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md'):
    s=before[name];start=s.index('手机已部署Linux #100（阶段101）')
    endline='保留15组硬件、Android、数据/GPT、SSH身份、旧显示快照和另一线程rootfs/F2FS；固件/镜像/身份/凭据/原日志仅私人目录。冷启动/休眠/长期稳定待办，全硬件goal仍active。\n'
    end=s.index(endline,start)+len(endline)
    s=s[:start]+common+s[end:]
    s=s.replace('session101](sessions/101-adsp-native-apr-reply-and-radio-regression.md)',f'session102](sessions/{session})')
    s=s.replace('session101](../sessions/101-adsp-native-apr-reply-and-radio-regression.md)',f'session102](../sessions/{session})')
    if name.endswith('HARDWARE-STATUS.md'):
        s=s.replace('2026-10-11，session101','2026-10-11，session102')
        s=s.replace('| 原生显示面板 | ','| 原生显示面板 | #101当前checkpoint两次超时，历史失败继续；',1)
        s=s.replace('| Wi-Fi | ','| Wi-Fi | #101首次自动初始化成功、MPSS运行超过628秒、5GHz网关3/3/DNS/HTTP通过，无手动恢复；仅一次暖启动，不能宣称可靠性修复。',1)
        s=s.replace('| 蓝牙 | ','| 蓝牙 | #101自动同机DMS身份成功，两次phase2错误；用户关闭后HCI控制器移除，无配对连接。',1)
        s=s.replace('| 蜂窝网络/数据 | ','| 蜂窝网络/数据 | #101一次首次暖启动成功，不能覆盖99–101失败或当作蜂窝验收；',1)
        s=s.replace('| 振动 | ','| 振动 | #101按真实驱动/DT解析为2-005a，ID97/standby/error0、starts0；',1)
        s=re.sub(r'^\| 音频 \|.*$', '| 音频 | #101 ADSP运行/AFE7/ASM2；WCD934x ID0x108/0x1、SLIMbus及codec绑定通过；双MAX98937实际ID0x43，错MAX98927组件已解绑、复位低，ALSA无卡 | 正确MAX98937驱动/声卡/DAI与MI2S/SLIM路由；扬声器、麦克风、耳机及冷启动/休眠 |',s,flags=re.M)
        s=s.replace('下一项继续音频codec/SLIMbus/功放与声卡；','下一项继续正确MAX98937驱动、声卡/DAI与播放录音；',1)
    (root/name).write_text(s)
with tarfile.open(out/'checkpoint.tar') as tar:
    dmesg=tar.extractfile('k102-checkpoint/dmesg.txt').read().decode()
display=[l for l in dmesg.splitlines() if 'frame done timeout' in l]
native=json.loads((out/'kernel-validation.json').read_text())
candidate=json.loads((out/'candidate-validation.json').read_text())
content=f'''# session102：WCD934x接入与真实双MAX98937识别

2026-10-11，Linux #101已通过F1飞轮刷入boot/logdump。WCD934x实际ID major0x108/minor0x1，SLIM SAT收到master capability、控制器注册、codec绑定与原生AFE API7/ASM API2回复通过。ALSA仍无卡，播放/录音未验收。

本机实际左右功放是MAX98937，不是名称暗示的MAX98927：0x39和0x3a在0x01ff均返回0x00，在0x0600均返回0x43。最初原生MAX98927组件仅绑定，尚无声卡触发其component初始化；错误组件已正常解绑，两条复位线最终物理低。没有功放寄存器数据写入、没有PCM/声音输出；下一步先修正型号/驱动，再接机器声卡与DAI。

本次首次MPSS自动启动成功（up44.627426秒），Wi-Fi worker result0/WIFI_READY；checkpoint uptime {check['uptime_seconds']}秒，MPSS连续运行{check['mpss_running_seconds']:.6f}秒，未手动恢复。5GHz通过认证、DHCP、路由、DNS及577字节HTTP，网关3/3回复。仅一次暖启动；initramfs/无线代码不变，不能把这次成功归因于某个音频节点或宣布首轮fatal已修复。历史99–101失败、2.4GHz reason7/删除等待、冷启动/休眠/长期稳定保持待办；热点配置仍为私人临时测试配置，未内嵌自动连接。

蓝牙自动地址查询完成并保持未配对，用户关闭后控制器从/sys/class/bluetooth移除；本轮两次phase2/115200/chunk1/partial0/first00错误保留。振动ID97/standby/error0/starts0；用户无人测试，机械确认暂缓，没有待答问题或新增播放。

125文件checkpoint SHA `{check['checkpoint_sha256']}`。3个完整原包逐字节绑定、首个不完整collector保留、所有nested manifests纳入外层SHA清单；boot/logdump完整读回、运行FDT、原模块/服务、6个NV源及persist不变通过。两个DSP running、taint0，SMMU fault0，显示超时2：

```
{chr(10).join(display)}
```

显示故障独立保留，不能用本轮早期205秒timeout0覆盖当前两次或历史快照；本轮未打开单播删除跟踪，不能报“删除问题修复”。

原厂契约：只读原sde17 DTBO24MiB，源/副本/之后哈希相等；vendor以ro,noload/nosuid/nodev/noexec挂载并卸载，33私有文件归档通过。两份overlay中MTP board-id8匹配本机19781，SDX50M条目不采用。Tavil的元素地址、IRQ123、MCLK9.6MHz、reset143与五路S4 1.8V已核对；micbias2为2.7V，其它1.8V。原生MFD逻辑0→1与物理SYS_RST_N低→高对应ACTIVE_HIGH，原生MAX复位逻辑1→0对应ACTIVE_LOW。

QUP4 I2C实际寄存器0x890000、IRQ605、GPIO51/52；原厂SPI覆盖GPIO53/54不是I2C映射，GPIO54保持触屏复位。新增总线使adapter编号变化，当前功放1、振动2、触摸4；helper按唯一驱动+完整DT路径识别振动，不依赖旧1-005a。当前源DTS仍有MAX98927兼容候选，**实机已解绑，后续必须修正；不能直接重绑定后启用声卡/扬声器**。

SLIM资源由同机19781基树与固定SM8150公开参考互证：NGD0x171c0000/IRQ163、BAM0x17184000/IRQ164、SID0x1b46；采用原生BAM/NGD/PDR及严格SMMU映射，不扩大mask或旁路。仅新增9个DT节点、i2c4 status/100kHz与10个音频配置变化，initramfs/模块逐字节一致，其它已修改源码保持。真正EDK2重建只替换DTB FFS/压缩容器，compat/shim/ramdisk/执行代码/EUD/F1源保持。

参考源码为[Realme官方自定义功放实现](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/audio-kernel/asoc/codecs/max989xx/max98937.c)：虽然L/R compatible写max98927，presence会检查两个型号的只读版本地址，reset为低1ms→高→20ms。源码GPL2，头文件由该实现使用；不移植其全量配置/DSM或共享static生命周期逻辑。ID工具只在ALSA无卡、两native组件解绑、精确QUP4/TLMM身份后运行；普通I2C_SLAVE拒绝绑定地址，未用FORCE；仅两种版本寄存器的地址指针+读字节，GPIO只访问已核实的148/37，完成后复位低。

同SoC公开参考：[固定403b56 SM8150资源](https://github.com/ClearStaff/linux-sm8150-mainline-hotdog/blob/403b56c33e2ccdda25d90378970a5e5b928dee19/arch/arm64/boot/dts/qcom/sm8150.dtsi)及[WCD9340](https://github.com/ClearStaff/linux-sm8150-mainline-hotdog/blob/403b56c33e2ccdda25d90378970a5e5b928dee19/arch/arm64/boot/dts/qcom/sm8150-wcd9340.dtsi)。仅参考互证资源，未套用其它机型功放/card。

失败与边界：首个pin查询用了不存在的3400000路径；fresh guard后转正确3100000并另存。准备guard遗漏51/52时在修改前停止；补完整现场后继续。分块脚本旧#99 guard在任何分块前失败，改#100后新前缀完成。首次runtime collector的i2c-adapter class路径不存在，完整partial保留，重采新retry1包。首次网络流程已完成所有网络项，但关闭并移除BT后旧mgmt info超时；completion只归档并验证原网络结果与空HCI，无重启BT、无重测覆盖。GitHub API403，固定commit filtered Git取源码；无GPL头的build recipes触发guard后停止，限定C/H恢复并保留错误记录。初次FDT audit未列UEFI五个运行期chosen字段而失败，补字段值/descriptor版本与对齐校验，未放宽任何硬件节点差异。

80个2MiB备份块/8192Kbit/s全部SHA通过；并发只读SSH一次连接超时后成功重读，SCP未重放失败块。F1 receipt后EUD EIO/设备退出保留；独立fastboot身份/产品/96MiB boot/64MiB logdump验证后刷入。本次postflash EUD读取7.578秒后EIO，保存原raw/events/usbmon；完整内核证据来自NCM设备归档，不把截断EUD当完整日志。

Image `{native['image_sha256']}`；DTB `{native['dtb_sha256']}`；CPIO `{native['cpio_sha256']}`；boot `{candidate['boot_sha256']}`；logdump `{candidate['logdump_sha256']}`；完整boot读回 `4b3e76ae4c1ea5da894f219c20e5ca680785afd880dc2dd9fce09a3f914566ea`。

下一项：[MAX98937、声卡及全硬件交接](../reference/kernel102/next-session.md)。固件/OEM XML/库/原DTBO/原日志/身份/密码/镜像/二进制只在私人目录，无commit/push；Android/GPT/userdata/原NV/persist/SSH/显示快照/rootfs01保持，全硬件goal active。
'''
(root/'sessions'/session).write_text(content)
handoff=f'''# 下一阶段：正确MAX98937驱动与音频声卡（session102）

继续全硬件goal。先读[session102](../../sessions/{session})、[15组硬件](../../linux-port/docs/HARDWARE-STATUS.md)、本目录README与私人 E:/edk2-samurai-out/kernel102/checkpoint-validation.json。每轮重新核对真实boot ID/uptime/进程/目录/驱动/路由/哈希；既有目录/PID和旧adapter编号不能重放。

{common}

当前手机Linux #101、initramfs未改。最新125文件checkpoint SHA `{check['checkpoint_sha256']}`，uptime673.35、MPSS已运行628.722574秒，worker自动result0、5GHz COMPLETED，双DSP running/taint0，显示超时2、BT phase2错误2。历史首次MPSS失败与2.4GHz掉线没有关闭。蓝牙已正常stop，HCI空；不为mgmt info重新启动它。用户振动机械确认暂缓，不再提问或重放脉冲。

**先修正实际MAX98937，不能继续拿MAX98927组件播放。** 原厂GPL源固定9668fcdc的audio-kernel/asoc/codecs/max989xx/max98937.c/.h已保存在 /home/cy122/x2pro-linux/refs/realme-amp-git-k102，private oem-amp-git-provenance.json记录来源/哈希。其presence检查01ff/0600的bit0x40；本机双通道实测00/43。MAX98937的global enable=0500、soft reset=0501、revision=0600；不能使用MAX98927的00ff/0100/01ff寄存器图。不要整体套用OEM DSM/增益/保护配置或共享static生命周期代码；逐项核对左右通道表、I2S时钟和保护后写自己的正确驱动，ID有效前拒绝配置。当前两个native MAX98927组件已解绑、reset GPIO148/37物理低且unclaimed，WCD934x-codec组件继续绑定；没有ALSA卡/PCM。

下一步实现MAX98937准确DTS/驱动与原生ASOC组件，保留ID-first/失败停机。再接AFE/ASM/ADM、SM8150机器声卡、SLIM codec链和QUAT MI2S3功放链；原厂确认speaker-vendor=maxim、speaker-i2s-id3。每个SLIM rtd配置channel map，避免其它机型per-card全局标志缺陷。先真实PCM时钟/数据/录音，再可控低强度声音；无人物理确认时按日志/代码推进并记录边界，不能把注册卡当声音输出。

codec契约已真机验证：SLIM217:250:1:0与ifd217:250:0:0、reset143ACTIVE_HIGH对native0→1、IRQ123LEVEL_HIGH、LN_BB_CLK2/extclk/MCLK9.6MHz、五路S4a1p8、micbias1/3/4=1.8V及2=2.7V。MBHC buttons threshold缺省warning尚在，声卡/耳机阶段按同机源码校准。SoundWire无本机WSA扬声器，不因共有overlay旧WSA节点而启用它们。NGD/BAM基地址、IRQ和SID0x1b46已互证并真机无SMMU fault；其它音频DMA/ASM资源仍须验证。

QUP4真正是890000/IRQ605/51+52，GPIO54触屏复位保留；本轮motor=2-005a，touch=4-0020，不能重用过去1-005a/3-0020。/tmp/k102-haptics-device按唯一AW8697驱动与完整89c000 DT路径查找。/usr/sbin/samurai-modem-remoteproc同样按唯一设备身份解析MPSS，不假设remoteproc0；ADSP按name/PAS/FW/DT解析，不能强制crash或循环恢复。

新一轮完整boot/logdump备份+真实镜像/FAT/FFS审计。DTB变更必须重建实际EDK2；只刷boot/logdump，NV只RAM COW。currentImage/DTB/CPIO/boot/logdump哈希见session102/private validation，fresh boot ID使用kernel102/runtime-boot-id-after-private.txt。私有5GHzprofile使用kernel102/wpa-5g-private.conf（5180）；旧kernel95 profile限制2.4GHz，勿误用。只有自动真实失败且首轮日志保留后才能一次有界恢复；本轮完全没有运行备用manual recovery脚本。

保留15组功能、充电收尾不跑旧OEM/配置/NV/OTP/FET/OTG/MCU/I2C_FORCE探针、显示85–88失败快照、Android/原NV/persist/GPT/data/SSH及另一rootfs01线程全部文件和F2FS段落。不提交推送，不公开固件/OEM XML/库/二进制/原日志/身份/密码。首次MPSS/2.4GHz/删除等待、显示超时、BT脉冲、USB传输、冷启动/休眠待办持续；摄像头/SLPI传感器/指纹/蜂窝/GNSS等剩余功能仍在全硬件目标内。

当前阶段102代码包含构建前guard失败及运行partial的原脚本，不能盲目重放prepare/collector/backup/flash；使用新编号/前缀并重新审计。实际完成的runtime为retry1，net为auto-network-completion，amp为amp-readonly-ids，最终checkpoint涵盖nested manifests。公开原脚本与出错边界是历史证据，不是无条件可执行的当前命令。
'''
(ref/'next-session.md').write_text(handoff)
(root/'NEXT-SESSION.md').write_text(handoff.replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/'))
(root/'NEXT-SESSION-PROMPT.md').write_text('继续Realme X2 Pro全硬件Linux适配，下一步修正实测MAX98937驱动、接音频声卡/DAI。先读NEXT-SESSION.md、sessions/102、reference/kernel102及私人kernel102/checkpoint-validation.json，重新核对真实boot ID/进程/目录/哈希。Linux #101已真实刷boot/logdump，WCD934x ID0x108/0x1、SLIM/codec与AFE7/ASM2通过；双功放01ff=00、0600=43证明MAX98937，错MAX98927组件已解绑、GPIO148/37复位低，无卡/PCM/输出，不能重绑定错驱动播放。本次一次首次暖启动MPSS与Wi-Fi自动初始化成功、5GHz认证/DHCP/DNS/HTTP/网关3/3，通过125文件checkpoint/80块备份/部署读回/NV与persist不变；不能宣布历史40秒fatal/2.4GHz reason7/删除等待已修复。当前双DSP running、taint0、显示超时2/BT phase2错误2；蓝牙已stop且HCI空，不配对连接；振動无人测试，机械确认暂缓、没有待答问题，不重放脉冲。QUP4实际51/52，GPIO54触屏保持；I2C编号已变，按唯一驱动/DT解析设备，MPSS用named helper。原厂GPL自定义MAX98937源码已固定commit，逐项核对寄存器/通道/保护，勿套MAX98927图或其它手机功放/card。保留15组硬件/Android/data/GPT/NV/persist/SSH/旧显示/rootfs01/F2FS；充电不重跑旧探针，NV仅RAM COW，只刷boot/logdump，DTB须真正EDK2重建。原日志/固件/OEM配置/身份/凭据/镜像/二进制只私人，无提交推送。全硬件goal active。\n')
(ref/'README.md').write_text(f'''# kernel102：WCD934x与实际MAX98937识别

Linux #101已真实部署，codec/SLIMbus及API回复通过；实际双MAX98937 ID0x43已确认，错组件解绑/复位低，尚无ALSA卡。首次自动无线一次暖启动成功，5GHz网关3/3/DNS/HTTP通过；历史可靠性待办保持。

见[session102](../../sessions/{session})、[下一阶段](next-session.md)。125文件checkpoint `{check['checkpoint_sha256']}`，完整3原包/nested清单/运行FDT/读回/NV/persist通过。显示超时2，蓝牙关闭移除、无配对连接，振动确认暂缓。

本目录只含自写源、脚本、补丁和脱敏说明。stock contract/固定primary源码/provenance、prepare/build/audit、真实EDK2/package/backup/flash、runtime retry1、网络completion、精确haptics-device、ID-only GPIO/I2C诊断及checkpoint工具按阶段保存。签名固件、原DTBO/XML/库、原日志、身份/密码、镜像/二进制全部私人。

构建前与运行时guard错误原脚本/partial保留；已有目录不可重放。当前DTS保留最初MAX98927候选，但实际已解绑；下一轮先正确MAX98937驱动与DTS，不能直接启用机器声卡/扬声器。充电、rootfs01、Android/数据及原NV保持。
''')
s=before['HANDOVER-NEXT.md']
line=next(l for l in s.splitlines() if l.startswith('当前交接见 '))
s=s.replace(line,f'当前交接见 [阶段102](sessions/{session}) 与 [NEXT-SESSION](NEXT-SESSION.md)：Linux #101，WCD934x通过、实际双MAX98937已识别，错组件解绑/复位低，声卡待接入；一次自动无线/5GHz通过，历史稳定性待办保留，蓝牙关闭。以下阶段88记录保留历史上下文。')
(root/'HANDOVER-NEXT.md').write_text(s)
s=before['DOCS-INDEX.md'];line=next(l for l in s.splitlines() if l.startswith('当前：'))
s=s.replace(line,f'当前：[阶段102](sessions/{session})、[阶段101](sessions/101-adsp-native-apr-reply-and-radio-regression.md)、[下一阶段](NEXT-SESSION.md)。')
s=s.replace('| linux-port/docs/HARDWARE-STATUS.md | 按用户功能分组的14类硬件接入/验收状态与优先级 |','| linux-port/docs/HARDWARE-STATUS.md | 按用户功能分组的15类硬件接入/验收状态与优先级 |')
(root/'DOCS-INDEX.md').write_text(s)
(root/'reference/kernel101/next-session.md').write_text('后续实际状态已推进至[阶段102交接](../kernel102/next-session.md)：WCD934x通过、真实双MAX98937已识别并解绑错组件；一次自动无线成功，历史失败仍开放。以下保留阶段101历史交接。\n\n'+before['reference/kernel101/next-session.md'])
print('AUDIO_IDENTIFICATION_DOCS_UPDATED')
print('DISPLAY_TIMEOUT_LINES='+json.dumps(display))
