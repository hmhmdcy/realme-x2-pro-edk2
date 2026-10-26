from pathlib import Path
import hashlib, json
root=Path('/mnt/e/RealmeX2Pro edk2')
ref=root/'reference/kernel101'
out=Path('/mnt/e/edk2-samurai-out/kernel101')
check=json.loads((out/'checkpoint-validation.json').read_text())
candidate=json.loads((out/'candidate-validation.json').read_text())
kernel=json.loads((out/'kernel-validation.json').read_text())
assert check['checkpoint_audit_pass'] and check['adsp_native_version_reply_pass']
names=['README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md',
       'NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','HANDOVER-NEXT.md','DOCS-INDEX.md',
       'reference/kernel100/next-session.md']
assert not (out/'public-docs-before.json').exists()
before={name:(root/name).read_text() for name in names}
(out/'public-docs-before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2)+'\n')
common='''手机已部署Linux #100（阶段101），ADSP自动加载本机签名固件并运行，APR原生版本回复AFE API7/ASM API2通过；ALSA尚无声卡，扬声器/麦克风/耳机未验收。
振动FF/电气状态、close/SIGKILL/1秒看门狗已通过；用户无人测试，按日志和代码复查暂缓机械确认，继续音频，无新增振动播放。
首次MPSS仍在up后39.986571秒fatal，自动无线启动失败；一次有界手动恢复后MPSS与ADSP均running、taint0、5GHz认证/DHCP/DNS/HTTP通过，蓝牙关闭、不配对连接。
误用早期2.4GHz配置的原失败保留，该频段又出现一次非主动reason7；改用已验证5GHz配置后网关首轮2/3回复，后续5/5无丢包，不能宣称无线稳定性修复。
当前113文件checkpoint/5包原现场绑定/80块完整备份/boot与logdump读回/6NV与persist不变通过；当前checkpoint显示超时0、三次BT错误均phase2，历史显示与删除等待问题保持。
DTB改变已真正重建EDK2；新增私有ADSP固件、按本机身份寻找MPSS的服务及只读版本查询，已有init/模块/振动驱动保留。下一项核对codec/SLIMbus/功放并接入声卡。
保留15组硬件、Android、数据/GPT、SSH身份、旧显示快照和另一线程rootfs/F2FS；固件/镜像/身份/凭据/原日志仅私人目录。冷启动/休眠/长期稳定待办，全硬件goal仍active。
'''
old_start='手机已部署Linux #99（阶段100）'
old_end='保留Android、数据/GPT、SSH身份、旧显示快照和另一线程rootfs/F2FS；固件/镜像/身份/凭据/原日志仅私人目录。\n'
session_name='101-adsp-native-apr-reply-and-radio-regression.md'
for name in ('README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md'):
    text=before[name];start=text.index(old_start);end=text.index(old_end,start)+len(old_end)
    text=text[:start]+common+text[end:]
    text=text.replace('session100](sessions/100-all-source-readiness-and-first-mpss-crash.md)',f'session101](sessions/{session_name})')
    text=text.replace('session100](../sessions/100-all-source-readiness-and-first-mpss-crash.md)',f'session101](../sessions/{session_name})')
    if name.endswith('HARDWARE-STATUS.md'):
        text=text.replace('2026-10-11，session100','2026-10-11，session101')
        text=text.replace('| 音频 | 未验收 | ADSP、音频路由/codec/功放，扬声器、话筒及耳机 |',
          '| 音频 | #100 ADSP自动加载本机固件/running；真实APR版本回复AFE API7/ASM API2；MPSS恢复期间ADSP保持运行，ALSA无声卡 | 本机原厂dtbo/codec/SLIMbus/功放身份、声卡路由；扬声器、麦克风、耳机、冷启动/休眠 |')
        text=text.replace('用户机械触感确认仍待答；本机profile/Shipping API核对、强度/效果、冷启动/休眠/恢复；GO/STATE不等同物理输出',
          '用户无人测试，暂缓机械确认并继续下一硬件；Shipping API28已核对；强度/效果、冷启动/休眠/恢复仍未验；GO/STATE不等同物理输出')
        text=text.replace('下一项优先振动机械确认及其它硬件接入；同时保留','下一项继续音频codec/SLIMbus/功放与声卡；振动机械确认由用户暂缓，同时保留')
        # Keep historical detail in the remaining rows and add the new evidence.
        text=text.replace('| Wi-Fi | 本机board/API5/MPSS/ath10k；', '| Wi-Fi | #100又一次首次MPSS约40秒fatal，自动失败；手动恢复后5GHz认证/DHCP/DNS/HTTP、网关后测5/5通过；又一次2.4GHz reason7、首轮网关2/3回复保留。本机board/API5/MPSS/ath10k；')
        text=text.replace('| 蓝牙 | UART13/hci0/revision21；','| 蓝牙 | #100独立DMS/关闭策略通过，三次phase2错误保留；UART13/hci0/revision21；')
        text=text.replace('| 原生显示面板 | 75光学/84翻页通过；','| 原生显示面板 | #100当前checkpoint未见超时，不能覆盖历史失败；75光学/84翻页通过；')
        text=text.replace('#99暖启动ID97/standby/error0','#99/#100暖启动ID97/standby/error0')
    (root/name).write_text(text)
handoff=f'''# 下一阶段：音频codec、SLIMbus、功放及声卡（session101）

继续用户全硬件goal。先读 [session101](../../sessions/{session_name})、本目录README、[15组硬件](../../linux-port/docs/HARDWARE-STATUS.md)及私人 `E:/edk2-samurai-out/kernel101/checkpoint-validation.json`。每轮重新读实际boot ID/uptime/进程/目录/驱动/路由/哈希；旧PID、starts=0脚本或已存在前缀不能重放。

{common}
用户已回答振动问题：“无人测试，先按照日志代码静态分析，没问题就下一个”。机械确认暂缓，**没有待答的振动问题，也不因缺少触感反馈阻止下一硬件**。代码复查未发现需立即修改的问题；保留阶段99三次20%150ms、close/SIGKILL/1.02秒看门狗及error0证据。当前starts0/standby，无重播；不把电气状态当机械输出。

本轮ADSP在18.900281秒up，保留本机原30MiB carveout `0x9b200000/0x1e00000/no-map`。本机modem分区RO取得17个拆分签名文件12,420,754字节，ELF32/Hexagon/可重定位段30MiB严格校验；只存私人输出/私有initramfs。固件JSN核对 `avs/audio` / `msm/adsp/audio_pd`，APR只描述core service3；SOUND/QDSP6/APR/PDR内建，codec/功放/机器声卡未启用。SLPI/CDSP保持禁用。

`q6core`本机只读 `samurai_api`调用原生GET_FWK_VERSION/不支持时legacy fallback；100ms单次等待、缓存，不走“timeout也ready”的API；sentinel要求真实服务4/7条目，拒绝缺失/超时。回复解析加入header与变长条目长度检查。实机首次/恢复后均AFE7/ASM2，ADSP恢复过程中持续running、无ADSP fatal、taint0。未打开PCM、未进行声音输出/录音，也无ALSA卡。

无线helper新增 `samurai-modem-remoteproc`，严格检查唯一name=modem、SM8150 MPSS compatible、真实DT路径及firmware名，不依赖编号。当前MPSS仍remoteproc0、ADSP remoteproc1，这只属本次启动；后续脚本一律动态解析。初始MPSS43.886772秒up、83.873343秒fatal，相隔39.986571秒，原boot-finished=1/自动日志保留；回收一次BT/ath10k/MPSS后running，NV仅复用已校验RAM COW。不能宣称自动启动修复或由ADSP引发已有40秒问题。

初次网络误用了旧 `freq_list=2462` 私有配置，2.4GHz认证成功但不满足5GHz测试条件；原partial目录/配置/失败保留，并观察一次非主动reason7（蓝牙关闭）。5GHz使用阶段100已验证私有配置重试；认证/DHCP/路由/DNS/HTTP577字节通过；首轮ping3发2收33%丢包，之后5发5收0丢包。原2.4GHzreason7和主动换5GHzreason3/locally_generated=1都保留，不以重测覆盖首轮丢包。没有重测双向4MiB或单播删除跟踪；历史阶段98证据与未解决项继续。

接下来：

1. 音频：只读核对本机未改动dtbo/原厂DT选择及vendor实际mixer路由，确认WCD934x SLIMbus/reset/IRQ/MCLK/供电与Maxim双功放具体芯片/接线。19781公开overlay是候选来源，当前通用vendor XML不能独自确定活动路由。先SLIMbus/codec枚举及ID，再机器声卡/DAI/功放；每步保留原声卡空与实际版本回复边界，不能把hotdog其它功放/资源直接套入本机。
2. 无线：给首轮MPSS空原因增加有限SMEM返回值/长度诊断，并收集QRTR/rmtfs请求链；先保留失败再做单次恢复。2.4GHz BT-off掉线、3.1秒删除无确认等待继续，勿盲增固定delay/无限重启或以公网ICMP失败替代HTTP结果。
3. 当前三次BT错误仍phase2/power-on pulse/115200/chunk1/partial0/first00；不改baud/parser/重试窗口作为掩盖。蓝牙继续不配对、不连接；NFC无标签先控制器；充电收尾不跑旧探针。
4. 下一次完整boot/logdump新备份；本次80x2MiB块8192Kbit/s全通过。只停止核对当前cmdline的自有SCP，不杀rootfs01任务。真实DTB改变须重建EDK2，F1 receipt后独立fastboot身份/产品/分区大小审计。ADSP不做强制crash，不循环DSP恢复；对照仓库有强制ADSP crash卡住PM的记录。

最终113文件checkpoint SHA `{check['checkpoint_sha256']}`，uptime {check['uptime_seconds']}秒，所有原包/nested清单/读回/服务及模块/6NV/persist通过；后续网关包uptime {check['gateway_followup_uptime_seconds']}秒、5/5、双DSPrunning。当前checkpoint显示超时0、BT错误3；这不消除旧显示失败、USB大传输/删除等待及冷启动/休眠/长期可靠性问题。

当前Image SHA `{kernel['image_sha256']}`；DTB `{kernel['dtb_sha256']}`；CPIO `{kernel['cpio_sha256']}`；boot `{candidate['boot_sha256']}`（{candidate['boot_bytes']}字节）；logdump `{candidate['logdump_sha256']}`。完整boot读回 `{check['full_boot_readback_sha256']}`，与新boot前缀+原分区尾部逐字节SHA相符。

Linux `/home/cy122/x2pro-linux/linux`，initramfs `/home/cy122/x2pro-linux/initramfs`，EDK2 `/home/cy122/edk2-samurai/repo`，私人 `E:/edk2-samurai-out/kernel101`。当前启动ID只存 `runtime-boot-id-after-private.txt`；不使用旧 `runtime-boot-id-private.txt`（#99刷入前）。HEAD仍e42788eafb0bb9d8dfce319c71ca54c5207b2295/f23a9f8aa619388412c8aad5834a460e51eae9eb，无提交/推送。实际DTS在WSL及本目录after快照；linux-port/dts旧镜像保持原件，不能直接构建。

只刷boot/logdump，保留Android/userdata/GPT/原NV/persist/SSH身份/显示85–88快照/rootfs01及F2FS段落。NV仅RAM COW；签名固件/镜像/二进制/OEM库/XML/原日志/身份/凭据/密钥不公开。充电相关配置/解封/NV/OTP/FET/OTG/MCU/GPIO不操作，不用I2C_FORCE。振动reset116与充电控制无关。
'''
(ref/'next-session.md').write_text(handoff)
(root/'NEXT-SESSION.md').write_text(handoff.replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/'))
(root/'NEXT-SESSION-PROMPT.md').write_text('继续Realme X2 Pro下一硬件Linux适配，优先音频codec/SLIMbus/功放与声卡。先读NEXT-SESSION.md、sessions/101、reference/kernel101和私人kernel101/checkpoint-validation.json，重新核对当前boot ID（after-private）/进程/目录/哈希。Linux #100已刷boot/logdump，ADSP本机签名固件自动运行并实际回复AFE API7/ASM API2，恢复无线时保持running/taint0；ALSA无卡，不能宣称声音可用。用户无人测试振动，已决定按代码和日志复查暂缓机械确认并继续下一项，没有待答的振动问题。MPSS首轮约40秒fatal/自动无线失败，原日志与boot-finished=1保留；一次有界恢复后5GHz认证/DHCP/DNS/HTTP通过，网关先2/3后5/5；2.4GHz又一次reason7，历史删除等待/显示/BT phase2问题保持，蓝牙暂不配对连接。核对本机原厂dtbo/活动vendor路由及codec/功放身份后逐步接入，不用其它设备替代本机契约；ADSP不强制crash/无限恢复。113文件checkpoint、80块完整备份、实际内嵌DTB/boot/logdump与RAM模块服务读回及6NV/persist不变通过。保留15组硬件/Android/userdata/GPT/原NV/persist/SSH/显示旧快照/rootfs01及F2FS段落。NV仅RAM COW，只刷boot/logdump；固件/OEM配置/原日志/凭据/身份/镜像/二进制只在私人目录，无提交/推送。全硬件goal仍active。\n')
text=before['HANDOVER-NEXT.md'];start=text.index('当前交接见 ');end=text.index('\n',start)
text=text[:start]+f'当前交接见 [阶段101](sessions/{session_name}) 与 [NEXT-SESSION](NEXT-SESSION.md)：Linux #100，ADSP真实版本回复通过、声卡未接入；振动机械确认由用户暂缓，5GHz手动恢复可用，首次MPSS崩溃/2.4GHz稳定性仍待修复。以下阶段88记录保留历史上下文。'+text[end:]
(root/'HANDOVER-NEXT.md').write_text(text)
text=before['DOCS-INDEX.md'];start=text.index('当前：');end=text.index('\n',start)
text=text[:start]+f'当前：[阶段101](sessions/{session_name})、[阶段100](sessions/100-all-source-readiness-and-first-mpss-crash.md)、[下一阶段](NEXT-SESSION.md)。'+text[end:]
(root/'DOCS-INDEX.md').write_text(text)
(root/'reference/kernel100/next-session.md').write_text('> 后续用户已暂缓振动机械确认；当前已部署#100音频DSP基础候选，见 [阶段101交接](../kernel101/next-session.md)。以下为阶段100当时的记录。\n\n'+before['reference/kernel100/next-session.md'])
(ref/'README.md').write_text(f'''# kernel101：ADSP原生版本回复与无线基线

2026-10-11，Linux #100已真实刷入boot/logdump，ADSP自动运行并通过AFE API7/ASM API2回复，尚无ALSA卡。用户暂缓振动物理确认，继续音频；当前5GHz经一次有界手动恢复可用，首次MPSS40秒fatal、2.4GHz新增reason7未解决，蓝牙关闭、不配对连接。

见 [session101](../../sessions/{session_name})、[下一阶段](next-session.md)。最终113文件checkpoint `{check['checkpoint_sha256']}`；所有原包/清单/读回/6NV/persist校验通过。

| 文件 | 用途 |
|---|---|
| collect-audio-preflight.sh、verify-preflight.py | 本机只读vendor/modem预检、固件跨度与内存校验，固件仅私人 |
| prepare-adsp.py、build-adsp.sh、audit-kernel.py | ADSP/APR DTS、配置、CPIO新增项与原文件保持审计 |
| samurai-modem-remoteproc、samurai-wifi、samurai-radio-address | 按唯一真实设备身份定位MPSS，不依赖remoteproc编号 |
| prepare-core-query.py、q6core-samurai-query.patch | 本机只读、实际回复支撑的原生版本查询与解析长度检查 |
| build-firmware.sh、verify-firmware.py、prepare-package.py | 真正重建EDK2嵌入DTB、FFS/FV/boot及FAT审计 |
| collect-preflash.sh、split-backups.sh、receive-backups.ps1、flash-adsp.ps1 | 新现场/完整备份/分块SHA/F1后独立fastboot及只刷boot/logdump |
| collect-audio-runtime.sh、verify-audio-runtime.py | 实际DSP/原生回复/空声卡/部署读回、原NV/persist |
| collect-boot-failure.sh、recover-after-mpss-crash.sh | 保留首轮失败，ADSP持续运行下单次恢复MPSS |
| test-recovered-network-retry1.sh、test-gateway-followup.sh | 私有5GHz认证/网络及首轮丢包后有界网关复测 |
| collect-checkpoint.sh、verify-checkpoint.py | 113文件、nested原包、源码/CPIO/RAM模块与运行状态审计 |

已有目录/PID/启动编号不可重放。初次目录guard、初次错误频段、首次清单遗漏nested manifest均保留失败原件；当前collector以唯一新前缀重采并覆盖校验所有nested manifests。签名固件、OEM XML/库、原日志、身份/凭据、镜像和二进制不在公开目录。
''')
(root/'sessions'/session_name).write_text(f'''# 101：ADSP真实版本回复、振动人工验证暂缓及无线基线

2026-10-11。本轮已构建并真实刷入Linux #100和重建的EDK2；本机ADSP自动运行、APR原生版本回复AFE API7/ASM API2通过。ALSA仍无声卡，音频输出/录音未验收。一次有界恢复后MPSS/ADSP running、5GHz可通信、蓝牙关闭；首次MPSS40秒fatal与2.4GHz掉线仍未解决。全硬件goal仍active。

用户明确无人测试振动，要求按日志与代码静态分析后继续下一个。复查ID检查、异步I2C、低强度连续模式、关闭/故障停振和1秒保护，未发现需要立即修改的问题。保留阶段99三次20%150ms电气与close/SIGKILL/1.02秒保护测试；Shipping API28核对通过；机械效果未人工确认且已暂缓，无新增播放、没有待答的触感问题。

## 本机资源与候选

预检在#99当前启动下完成，vendor ext4只读noload、modem vfat只读，均已卸载。40文件预检包SHA `3ad010286b3f33597ab8c6a387a559fd9581cd6421ebf88c745686d42af6a368`。本机17个ADSP拆分签名文件共12,420,754字节，ELF32/EM_HEXAGON164，load段可重定位跨度30MiB，与保留的 `0x9b200000/0x1e00000/no-map` 完全相符。签名内容/OEM XML/JSN只在私人目录。

本轮只修改ADSP status/firmware-name，新增APR/core两节点，domain4/channel apr_audio_svc；固件JSN核对avs/audio、msm/adsp/audio_pd。SOUND/QDSP6/APR及PDR内建；QDSP6其它服务的代码没有相应DT设备。codec/功放/机器声卡仍未启用；SLPI/CDSP禁用。原init、已有模块/驱动、保留区及其它DT节点保持；GPU zap同目录文件保持。两次构建的登录PATH导致8项Rust编译器检测元数据差异已逐项审计，CONFIG_RUST始终关闭，没有新增Rust运行代码。

公开19781资源来自 [Realme官方内核仓库](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source)。[hotdog维护者ADSP记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-05-mainline616-adsp.md)提供同SoC分步验证的参考；本机签名固件和实际结果单独核对。下一步音频契约仍需本机原厂DT选择和活动vendor配置确认，公开overlay提示WCD934x/Maxim并非已验收芯片结论。

新增无线helper严格核对唯一MPSS的name/compatible/DT真实路径/firmware；两个无线服务不依赖remoteproc0。此次实机MPSS0/ADSP1，但下次编号不能当契约。两个服务内容与新增helper之外，CPIO只新增17个私有ADSP文件；原SSH身份/模块/初始化/振动全部保持。

## 实际DSP查询

只读samurai_api只对本机创建，调用原生GET_FWK_VERSION及必要时legacy fallback；单次100ms等待与原生一次缓存。sentinel拒绝没有真实服务条目的“成功”返回，不走默认timeout亦ready的接口。回复解析先检查固定header与变长条目长度，避免无界num_services读取。

ADSP18.900281秒up，初次102.64秒现场与恢复后只读查询均回复AFE API7/ASM API2，内核taint0、ADSP fatal0。没有打开PCM、设置功放增益或声学测试；/proc/asound/cards为空，不能把版本回复当声音可用。

## 刷入、首次失败与单次恢复

当前boot/logdump完整新备份，80个2MiB块8192Kbit/s全部逐块/合并SHA通过，本轮无传输超时。真实EDK2重建只DTB FFS/压缩容器变化，其它执行字节、兼容DTB、shim/header/ramdisk/EUD核心源保持。F1 receipt后出现设备消失/EIO，保留原日志；独立fastboot核对私有身份、msmnile与两分区大小，通过后只刷boot/logdump。

首次EUD设置时控制设备尚未枚举，失败保留；控制设备出现后正常com-up/一次reader重试通过并释放owner。NCM重新枚举后第一次SSH尚无可用地址，空启动ID文件保留，再读真实新boot ID并检查#100/taint0。EUD读取4587帧，原包仅私人。

首次MPSS43.886772秒up、83.873343秒fatal without message，间隔39.986571秒。源准备成功但无WLAN身份成功标记，自动Wi-Fi exit1；原boot-finished=1/自动日志与首次失败包保持。上轮无ADSP时已经有约40秒问题，不能据新增ADSP归因。原生同一句fatal包含SMEM错误/零长度/空首字节路径，仍需有限诊断。

自动BT worker已经退出/锁释放后，单次受控停BT/解绑ath10k/停崩溃MPSS/重绑/启动，复用已核验RAM COW与存活tftp/rmtfs。WLAN出现后45秒监测通过，独立WLAN/BT只读DMS成功，BT关闭；ADSP全程running，版本回复相同。原自动失败标记未改为0，也没有无限恢复。

## 网络与验收边界

初次误用早期freq_list2462的私有配置，2.4GHz认证成功但5GHz条件失败，原partial目录/配置不覆盖。这段期间又出现一条非主动reason7（此前阶段98已有两次）；之后主动换5GHzreason3/locally_generated1单独记录。重试改用阶段100已验证私有5GHz配置，认证/DHCP/路由/DNS/HTTP577字节通过；首轮网关3发2收33%丢包，后测5发5收0丢包。原丢包不被后测覆盖，2.4GHz、自动启动和长期稳定未解决。

最终113文件checkpoint SHA `{check['checkpoint_sha256']}`，uptime586.99秒；原4个完整测试包与nested清单逐字节绑定，并保留初次错误频段partial目录。后测网关包SHA `{check['gateway_followup_sha256']}`，uptime646.07秒，同启动双DSPrunning/taint0。当前checkpoint显示超时0、三条BT Frame reassembly failed均phase2；没有开启本轮单播删除跟踪，不作删除等待修复结论。振动ID97/standby/starts0/error0；6NV与persist不变。

首次checkpoint collector遗漏nested清单的外层hash，原包保留，修改为只排除根SHA256SUMS，以checkpoint-retry1重采并全校验。初次原目录guard发现GPU已有固件而停止，私有前快照保留；核对只有两个无线服务和新helper的部分修改后有界续做，未覆盖GPU固件。所有工具/数据失败均有原件，不以日志删除改变验收。

## 产物与后续

| 产物 | SHA256 |
|---|---|
| Image #100 | `{kernel['image_sha256']}` |
| DTB | `{kernel['dtb_sha256']}` |
| CPIO | `{kernel['cpio_sha256']}` |
| boot（{candidate['boot_bytes']}字节） | `{candidate['boot_sha256']}` |
| logdump（64MiB） | `{candidate['logdump_sha256']}` |
| 完整boot读回 | `{check['full_boot_readback_sha256']}` |

boot整分区与新前缀+原尾部的SHA相符，logdump整分区与候选完全相符，RAM服务/已有模块及实际ADSP DT节点与候选吻合。当前源码见 [reference/kernel101](../reference/kernel101/README.md)，下一项 [codec/SLIMbus/功放交接](../reference/kernel101/next-session.md)，15组 [硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。

保留Android、userdata/GPT、原NV/persist、SSH身份、显示85–88和rootfs01/F2FS；NV仅RAM COW，不跑旧充电探针。签名固件/镜像/二进制/OEM库/XML/原日志/身份/凭据不公开，无提交/推送。冷启动/休眠/长期稳定及全硬件仍待继续。
''')
assert next(p for p in (root/'linux-port/README.md').read_text().split('\n\n') if p.startswith('2026-10-11 rootfs 进展：'))==next(p for p in before['linux-port/README.md'].split('\n\n') if p.startswith('2026-10-11 rootfs 进展：'))
print('ADSP_CHECKPOINT_AND_HANDOFF_DOCUMENTED')
