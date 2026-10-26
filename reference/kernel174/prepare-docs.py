from pathlib import Path
import hashlib, json, subprocess

ref=Path(__file__).parent
root=ref.parent.parent
out=Path('/mnt/e/edk2-samurai-out/kernel174')
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
final=json.loads((ref/'final-validation.json').read_text())
stop=json.loads((ref/'capture-stop-validation.json').read_text())
native=json.loads((ref/'dmic0-ucm174-low24-analysis.json').read_text())
desktop=json.loads((ref/'desktop-acoustic-validation.json').read_text())
build=json.loads((ref/'build-package-validation.json').read_text())
assert final['taint']==0 and final['machine_card_rebind_used'] and stop['real_pcm_pause_supported']
assert all(r['known_tone_detected_with_disabled_amp_control'] for r in native['speaker_decisions'])
assert all(r['detected_with_native_amp_off_reference'] for r in desktop['results'])
for n,h in build['source_sha256'].items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==h,n
assert (out/'k174-all-private.tar.gz').is_file()
report=dict(stage=174,kernel_build=174,logdump174_deployed=True,boot172_and_dtb172_retained=True,ucm173_retained=True,
 source174_verified=True,native_and_desktop_acoustic_regression_passed=True,capture_stop_and_pause_regression_passed=True,
 first_boot_soundcard_registration_failed=True,manual_machine_card_rebind_used=True,automatic_card_rebind_fix_pending=True,
 previous_kernel172_debugfs_name_oops_fix_pending=True,full_audio_goal_not_complete=True)
for folder in [ref,out]:(folder/'deployment-validation.json').write_text(json.dumps(report,indent=2)+'\n')

(ref/'README.md').write_text('''# 174：SLIM 端口中断停流、暂停回归与声卡重探测缺陷

2026-10-14。已部署 kernel174/logdump174，保留 boot172、DTB172、modules/software132、Mesa149、UCM173。端口中断补丁在声卡手工重新绑定之后，通过 8 次录音启停、3 次真实暂停/恢复，以及原生和桌面声学回归。首次启动的声卡重探测失败尚未修复；不能把本次回测写成正常启动或完整音频验收。

## 修改与软件验证

[增量补丁](wcd-port-lifecycle.patch)只改变 WCD934x：端口 IRQ 从 DAPM 上电移到 stream START/RESUME/PAUSE_RELEASE；先屏蔽、清理旧事件，再启用流和相应中断。STOP/SUSPEND/PAUSE_PUSH 先屏蔽对应端口，随后断开流并清理事件。更新只触及当前 stream port mask 的位，保留其它端口；寄存器设置失败返回错误，启动失败清理已分配流，停止失败仍尝试后续清理。

IRQ handler 对已经屏蔽的待处理端口事件只做确认，运行端口的 overflow/underflow 错误仍报告；读取失败不会使用未初始化值，错误端口屏蔽改为 regmap_update_bits。原厂同机型源码也检查中断是否启用，但其关闭等待机制与当前 SLIMbus API 不同，未照搬关闭等待。

[58 个实际 C 函数用例](host-tests-validation.json)覆盖 32 个端口编号、共享寄存器位保留、启动/暂停/恢复/停止顺序、8 个启动失败点、6 个停流失败点及 6 个 IRQ 读失败点。ASan/UBSan 通过；删去 STOP 屏蔽或 IRQ mask 检查的两个负对照都失败。checkpatch/diff check 通过；W=1 WCD 对象零警告。完整构建只有未修改 EUD 源的 inherited unused-function 警告。

[构建审计](build-package-validation.json)确认 DTB172、15 个显示源及配置保持；770 个模块与132兼容，仅两个模块的 build-id 不同。完整 FAT 回读、文件系统检查通过。只刷写 logdump，未重新构建或刷写固件；boot172 与 NV 在设备回读通过。Image174 SHA256 为 `4a074dff44498ae6fc366e9ff0a8896afe3d479038df50c8202051b8f66adff1`，logdump174 为 `2bd3cd106f7e20e14fac1d78529a8df60f2fc4e94870c1d4656c4df20c8676c3`。

## 恢复、首次启动失败与真实范围

在原172启动中读取 `/sys/kernel/debug/regmap/217:250:1:0/name` 触发 `regmap_name_read_file+0x54` Oops，taint128。故障属于读取前已运行的 kernel172，174未部署；原始日志保留私人目录，原因未修复，不继续重复读取该接口。受控停机后未刷分区，重新启动原172；[恢复验证](recovery-validation.json)确认 taint0、boot/logdump172/NV保持、UCM173默认 profile 自动恢复。

恢复时 fb0 blank 返回 EBUSY，CRTC仍 active。第一次显式 DRM disable 返回0，但关闭fd后 fbdev又恢复模式；没有把 syscall 成功当作显示已停。关闭当前启动的 fbdev_emulation，再用 DRM null modeset、关闭fd，连续状态检查才确认全部 CRTC inactive。该设置只属于停机启动，新启动自动恢复Y。两次切换均重新取启动身份、完成远程处理器/音频/显示停机和 F2FS freeze，一次F1收据后USB EIO，没有重复发送。

174首启14秒已检测WCD/初始化MBHC，约19秒 codec 重新探测后 `SLIMBUS_0_RX` 初始化报 -EINVAL，声卡消失，两个回测在读取声卡的前置条件失败，未发声。源码定位到 machine `jack_component` 保留旧 component；`samurai_setup_jack` 拒绝新 component，而 `jack_created` 也缺少卡生命周期清理。为何本次启动发生 codec 重探测仍需核对，不能未经证据称为已确认SSR。

另一个调查线索是未修改的 `drivers/mfd/wcd934x.c`：每次STATUS_UP使用非devm `regmap_init_slimbus`，失败、STATUS_DOWN和remove均未调用regmap_exit；DOWN只移除MFD子设备。需要核对regmap/debugfs与devm IRQ chip的状态/设备生命周期，这可能解释旧debugfs对象保留，但尚不能认定为本次Oops的已证实根因。

[一次 machine unbind/bind](card-rebind-validation.json)重建 card 私有状态并恢复声卡；之后所有174声学和停流结果都属于此恢复后的同一启动。不是自动重探测通过。后续永久修复须按 ASoC cleanup 顺序释放 jack：本树在 link exit 后才移除 component，card remove 位于 component remove 后；不能在晚期 card remove 中盲目调用已移除 codec。候选应覆盖 RX/TX共享、卡解绑/重绑定及失败清理，并补重新探测和启动回归。

## 实机回归

- [录音停止](capture-stop-validation.json)：8次FE录音，16/32/48kHz各有覆盖，后端按板级约束48kHz；每次帧数正确、RUNNING/closed见证。另用 libasound 同一PCM完成3次 PAUSED/RUNNING转换并读取暂停前后帧。所有SLIM trigger返回0，underflow/overflow/Port Closed、WARN/Oops/传输故障新增均0，mixer保持。
- [原生四例](dmic0-ucm174-low24-analysis.json)：左右编码能量相关系数0.9727/0.9856，目标功放关闭负对照差20.07/42.53dB，左右均检出。
- [桌面双向](desktop-acoustic-validation.json)：普通用户 paplay+parecord，经 Speaker sink/Mic source，左右相关0.9516/0.9633，对同启动原生功放关闭参考差18.99/41.46dB；sink/source volume和mute保持。不能据此评价人声音乐质量。
- [最终快照](final-validation.json)：538.8秒，taint0，underflow/overflow/Port Closed总数0，传输和内核故障0；保留首启ASoC注册失败1条。单Pulse CARD/alsa-card，HiFi (Mic, Speaker)，真实CARD两个jack off，PCM关闭，功放8/8启停配平且关闭/静音，17原控件恢复，NGD suspended，模块132/NV核验通过。

端口策略模块重启后缺失已解释：运行中 callaudiod 主动卸载 module-switch-on-port-available，并监测 sink/source 可用性选择端口。见[固定上游源码](https://gitlab.com/mobian1/callaudiod/-/blob/fe87a9267f1e074d19055d7a236e6b6f759af11d/src/cad-pulse.c)及[来源核验](callaudiod-source-validation.json)；本机二进制含对应卸载符号。173手工补载仅是当时现场动作，不代表应重复加载或改默认配置。实际耳机插拔/profile切换仍未验。

用户暂缺耳机，不重复询问。下一步优先 jack/card 重绑定生命周期和 debugfs Oops，再补人声音乐、瞬态、耳机实物、冷启动/休眠/长稳。当前174是手工恢复后通过功能回归的候选，完整目标保持 active。回退可用完整 boot172/logdump172+UCM173；171 SD1人工听音版本继续保留，不能用更早SD0组合替代。

私人证据位于 `E:/edk2-samurai-out/kernel174/k174-all-private.tar.gz`、两个声学包及恢复目录；手机 `/var/lib/samurai/k174*` 保留失败与恢复记录。公开目录只含脚本、补丁和脱敏结果。无新人工听音确认，无耳机实物验证。
''',encoding='utf-8')

(root/'sessions/174-port-interrupt-stop-and-card-reprobe.md').write_text('''# 174：端口中断停止回归与声卡重探测

2026-10-14。kernel174/logdump174 已部署，boot/DTB172与UCM173保持。声卡手工重绑后，8次录音启停、3次真实暂停恢复、原生四例和普通用户paplay+parecord双向检出左右编码音；WCD underflow/overflow/Port Closed总数0，最终PCM关闭、两功放8/8配平、taint0。

本轮还出现两项未闭环缺陷：在旧172中读取regmap debugfs name触发Oops，受控重启恢复；174首启codec重探测后machine残留jack_component导致声卡注册-EINVAL，手工unbind/bind恢复。当前结果依赖这次声卡恢复，不能记为正常重探测或启动验收。ASoC link exit在component remove之前，card remove在其后，后续jack清理要按此顺序实现。

UCM173默认profile在恢复172后自动加载；端口切换模块被callaudiod主动卸载，属于路由策略所有权，未修改启动配置强制重载。用户暂缺耳机；实物耳机、音质、冷启动/休眠及长期验证仍开放。

完整修改、58项C测试、构建/刷写、失败及来源核验见[174证据](../reference/kernel174/README.md)。此前[173路由及双向](173-ucm-headset-routing-and-desktop-duplex.md)、[172初始化](../reference/kernel172/README.md)、[171人工听音](../reference/kernel171/README.md)保留原测量范围。
''',encoding='utf-8')

(root/'NEXT-SESSION.md').write_text('''# Realme X2 Pro 当前检查点

用途：核对部署、源码、回退与待办。最后核对：2026-10-14，kernel174/logdump174、boot/DTB172、UCM173。停流、暂停及左右声道回测通过，但174首启声卡重探测失败，手工重绑后恢复；完整音频目标仍active。用户暂缺耳机，不重复问。操作规则见[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)。

## 最后核对的部署与范围

| 项目 | 结果 |
| --- | --- |
| 组合 | kernel174/logdump174，boot172/DTB172，modules/software132，Mesa149，UCM173/路由助手；174只刷logdump |
| 身份 | release仍带k132，按uname-v构建号判断；DRM按by-path；当前身份在私人kernel174/k174-all-private.tar.gz与手机k174-final |
| 174现场 | 538.8秒、taint0、单Pulse CARD/alsa-card，HiFi (Mic, Speaker)，jack off，PCM关闭，两功放8/8配平且关闭静音，17原控件恢复，NGD suspended、NV/模块132通过 |
| 音频回归 | 手工重绑后的同boot：8次录音启停、3次真实暂停恢复，underflow/overflow/Port Closed总数0；原生四例与用户paplay+parecord双向均检出左右，volume/mute保持。58项实际C用例通过 |
| 174首启缺陷 | codec重探测后machine保留旧jack_component，SLIMBUS_0_RX注册-EINVAL；一次sound unbind/bind恢复。jack/card生命周期未永久修复，不能称自动重探测/正常启动验收通过 |
| 旧172新增缺陷 | 读取regmap 217:250:1:0/name触发regmap_name_read_file Oops/taint128，已受控重启172恢复，原因未修复。当前174 taint0不代表此接口修复 |
| 端口策略 | callaudiod主动卸载module-switch-on-port-available并接管端口选择；不要照173手工补载强制重载。UCM173在恢复172启动自动恢复，实际耳机事件未验 |
| 显示/GPU | 165实屏交接/DPMS证据与147/149已修复GPU故障范围保持；174显示源保持163。冷启动、休眠与长期可靠性开放 |

依据：[174](reference/kernel174/README.md)、[173](reference/kernel173/README.md)、[172](reference/kernel172/README.md)、[171人工听音](reference/kernel171/README.md)、[168](reference/kernel168/README.md)、[165显示](reference/kernel165/README.md)。更多功能见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。171“两组都听到，来自手机”不移作174音质证据。

## 源码、产物与回退依据

- WSL `/home/cy122/pmos-samurai-kernel136/kernel` tracked六文件；174只在WCD934x增加stream端口IRQ生命周期，machine/MBHC/DTS保持172，NGD/messaging保持168，15显示源保持163。[源码和产物哈希](reference/kernel174/build-package-validation.json)。目录名/release不是构建号。
- boot172/logdump172完整原件保留，可配UCM173回退；171 SD1人工听音组合也保留。更早boot164/logdump168是SD0。161/166拒收原件保留，不混入当前验收。
- EDK2 BDS源码保持164，工作区生成Build固件保持172，FdtBlob已恢复旧129字节。174没有构建固件，不能将工作区当pristine132。
- UCM源码在linux-port/ucm2和scripts/samurai-audio-route.py，install-audio-ucm.py只装三个文件。UCM132原件在手机k173-source与私人k173-all-private.tar.gz；软件回退核对唯一alsa-card及发现模块。173漏卸载子模块造成三CARD的失败与恢复保留。
- Mesa149库及[0015补丁](linux-port/patches/0015-mesa-turnip-a640-vm-bind-iova-alignment.patch)保持；普通更新或旧rootfs132会覆盖，后续包/rootfs需纳入。150降级候选未部署。

## 续作与已知风险

1. 先核对当前身份、源码/产物和边界，继续goal；完整音频未完成。
2. 优先修machine jack/card重绑定：ASoC cleanup先link exit、再移除component、最后card remove。在有效codec阶段解除共享jack，card生命周期复位jack_created/component，覆盖RX/TX共享与失败清理，实测重探测/启动。不能在晚期remove调用已移除codec。174重探测触发原因也需核对。
3. 调查旧172 debugfs name Oops：未修改MFD WCD驱动STATUS_UP分配非devm regmap，失败/DOWN/remove没有regmap_exit，需核对其与devm IRQ生命周期；这是线索，未证实根因。保留失败证据，不将当前健康当修复。随后补音质/瞬态、实物耳机、冷启动/休眠与长稳。见[AUDIO-NEXT-SESSION-PROMPT](AUDIO-NEXT-SESSION-PROMPT.txt)。
4. 显示停机fb0 blank曾EBUSY；DRM disable成功后last-close又恢复fbdev。174工具通过仅当前启动关闭fbdev_emulation、null modeset及关闭fd后的连续CRTC检查处理，不仅看返回值。当前启动该参数Y；切换前重新核对，旧身份不得复用，F1后USB EIO不重复切换。
5. 电池/实体camera/完整传感器、蜂窝/GNSS/指纹/NFC与整机可靠性按[硬件清单](linux-port/docs/HARDWARE-STATUS.md)继续；165历史启动记录器已停止。显示DPMS使用DisplayConfig.PowerSaveMode，wlr-randr移除唯一输出曾使Phosh崩溃。

历史见[会话索引](sessions/INDEX.md)、[显示修复](sessions/display-handoff-152-165.md)，同步维护见[文档导航](DOCS-INDEX.md)。私人录音、身份、密钥和原始日志不发布。
''',encoding='utf-8')

(root/'AUDIO-NEXT-SESSION-PROMPT.txt').write_text('''在 E:\\RealmeX2Pro edk2 继续修复并实机验收原生Linux音频，goal保持active。先读 NEXT-SESSION.md、WORKING-BOUNDARIES.md、HARDWARE-STATUS、reference/kernel174/README.md，再查173/172/171/168。

当前kernel174/logdump174，boot/DTB172，modules/software132，Mesa149，UCM173。按uname-v识别，release仍带k132。当前身份在私人kernel174/k174-all-private.tar.gz及手机k174-final，切换前重新核对。WSL kernel136树tracked六文件，174仅改WCD934x端口IRQ，源码哈希见174构建审计；未开始175。15显示源保持163，NGD/messaging保持168。

174端口IRQ跟随stream启停，STOP先屏蔽再断流并清事件；START/RESUME/PAUSE_RELEASE重新配置。IRQ确认已屏蔽事件，仍报告运行端口错误，检查读取错误，update_bits保留其它端口。58实际C用例、ASan/UBSan、负对照、checkpatch、W=1和完整构建通过；770模块132兼容，DTB172保持，只刷logdump。

174首启14秒有MBHC/声卡，19秒codec重探测后SLIMBUS_0_RX -EINVAL、无声卡。原因是machine旧jack_component保留，jack_created同样缺清理；一次sound unbind/bind恢复。所有174回归依赖这次手工重绑，不能称自动重探测或正常启动验收。优先做175永久生命周期修复：本树soc_cleanup_card_resources先link exit再component remove，card remove位于其后；在有效codec阶段解除共享jack，card阶段复位标记，覆盖RX/TX共享和失败、重绑定。不要晚期调用已移除codec。重探测触发原因仍需核对。

恢复后8次录音启停、3次同PCM真实暂停/恢复通过；原生四例左右相关.9727/.9856、功放关闭差20.07/42.53dB；用户paplay+parecord相关.9516/.9633、差18.99/41.46dB。当前538.8秒taint0，underflow/overflow/Port Closed总数0；保留首启ASoC注册失败1条。单CARD/alsa-card，HiFi (Mic, Speaker)，jack off，PCM关、功放8/8配平关闭、17控件恢复、NV/模块132通过，NGD suspended。录音私人，171人工确认不算新音质证据。

旧172读regmap 217:250:1:0/name触发regmap_name_read_file+0x54 Oops/taint128，已受控重启后部署174，原因未修复。线索：未改drivers/mfd/wcd934x.c的STATUS_UP用非devm regmap_init_slimbus，失败/DOWN/remove无regmap_exit，DOWN只移MFD子设备；核对regmap/debugfs与devm IRQ生命周期，未证实根因。停机fb0 blank EBUSY、DRM last-close恢复fbdev，已用仅当前启动关fbdev_emulation+null modeset+关闭fd后连续检查处理；新启动Y。

UCM173文件和安装器保持；恢复172后默认profile自动恢复。callaudiod会主动卸载module-switch-on-port-available并接管端口选择，上游固定源码与本机符号证据在174；不要为模块缺失强制补载或改启动配置。实际插拔/profile未验。用户暂缺耳机，不重复问。后续补debugfs Oops、音质/瞬态、实物耳机、冷启动/休眠/长稳。

回退可用boot172/logdump172+UCM173；171 SD1人工出声组合保留，更早164/168是SD0。UCM132原件在k173-source/私人173包，恢复文件需核对唯一子模块。当前启动与旧重启身份不能混用；F1后USB EIO不盲目重发。保护NV/校准与私人数据，不绕保护盲增功放，蓝牙只扫描不连接，振动不新增脉冲。
''',encoding='utf-8')

p=root/'linux-port/docs/HARDWARE-STATUS.md'
s=p.read_text()
a=s.index('用途：');b=s.index('\n\n**',a)
s=s[:a]+'''用途：当前硬件验收清单。最后核对：2026-10-14，kernel174/logdump174、boot/DTB172、software/modules132加Mesa149和UCM173。174手工声卡重绑后停流/暂停/原生及用户双向回归通过；首启重探测失败及旧172 debugfs Oops尚未修复。显示实屏证据属于165。以[音频174](../../reference/kernel174/README.md)、[173](../../reference/kernel173/README.md)、[171人工听音](../../reference/kernel171/README.md)、[显示165](../../reference/kernel165/README.md)、[GPU149](../../reference/kernel149/README.md)为准；规则见[WORKING-BOUNDARIES](../../WORKING-BOUNDARIES.md)。'''+s[b:]
lines=s.splitlines(True)
for i,line in enumerate(lines):
    if line.startswith('| 音频 |'):
        lines[i]='| 音频 | 171人工确认双组滴声；172偏置/绑定与UCM173耳机数字路由；174手工重绑后8次录音启停、3次真实暂停恢复、原生及用户paplay+parecord左右检出，WCD端口误报总数0、taint0、PCM/功放关闭；callaudiod接管端口策略 | 174首启codec重探测后旧jack_component导致声卡-EINVAL，需永久卡生命周期修复；旧172 regmap name Oops未修复。用户暂缺耳机，实物插拔/profile/声道/耳麦/按钮未验；音质、瞬态、声学保护、冷启动/休眠及长稳开放 |\n'
p.write_text(''.join(lines),encoding='utf-8')
p=root/'linux-port/ucm2/README.md'
s=p.read_text()
s+='\nOn the current Phosh system, callaudiod owns port selection and deliberately unloads PulseAudio module-switch-on-port-available. Its absence after startup is expected; do not add a second routing policy solely because that module is missing. See [174 source and reboot evidence](../../reference/kernel174/README.md). Physical insertion and profile selection remain unverified.\n'
p.write_text(s,encoding='utf-8')
assert (root/'NEXT-SESSION.md').stat().st_size<=6500
assert (root/'AUDIO-NEXT-SESSION-PROMPT.txt').stat().st_size<=4000
print('K174_DOCS_AND_SOURCE_CHECKPOINT_WRITTEN',flush=True)
