from pathlib import Path
import hashlib, json

ref=Path(__file__).parent;root=ref.parent.parent;out=Path('/mnt/e/edk2-samurai-out/kernel175');k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
final=json.loads((ref/'final-validation.json').read_text());build=json.loads((ref/'build-package-validation.json').read_text())
native=json.loads((ref/'dmic0-ucm175-low24-analysis.json').read_text());desktop=json.loads((ref/'desktop-acoustic-validation.json').read_text())
assert final['taint']==0 and final['parent_rebind_reliability_not_fixed']
assert all(r['known_tone_detected_with_disabled_amp_control'] for r in native['speaker_decisions'])
assert all(r['detected_with_native_amp_off_reference'] for r in desktop['results'])
for n,h in build['source_sha256'].items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==h,n
assert (out/'k175-all-private.tar.gz').is_file()
reprobe=dict(stage=175,completed_cases=final['completed_reprobe_cases'],complete_reprobe_suite_passed=False,
 second_parent_bind_timed_out=True,known_fault_counts=final['known_parent_rebind_fault_counts'],
 current_card_present_after_failure=True,current_taint=0,test_restoration_bind_receipt=False,
 driver_reprobe_after_timeout_seen_in_private_log=True,initial_test_idle_oracle_corrected_from_three_seconds=True,
 dead_old_debugfs_handles_verified_in_completed_cases=4,parent_reset_logical_address_or_settle_cause_not_yet_proven=True)
deployment=dict(stage=175,kernel_build=175,variant='v4',logdump_sha256=build['logdump_sha256'],image_sha256=build['image_sha256'],
 source175_verified=True,boot172_dtb172_ucm173_and_modules132_preserved=True,initial_automatic_card_recovery_passed=True,
 codec_rebind_and_one_parent_rebind_passed=True,parent_rebind_reliability_incomplete=True,
 native_stop_pause_and_desktop_acoustic_regression_passed=True,full_audio_goal_not_complete=True)
for folder in [ref,out]:
    (folder/'reprobe-validation.json').write_text(json.dumps(reprobe,indent=2)+'\n')
    (folder/'deployment-validation.json').write_text(json.dumps(deployment,indent=2)+'\n')
(ref/'README.md').write_text('''# 175：jack、regmap、MCLK 生命周期修复与父设备复位超时

2026-10-14。已部署 kernel175 V4/logdump175，保留 boot172、DTB172、modules/software132、Mesa149、UCM173。首启 codec 两次初始化后声卡自动恢复，不再需要174的 machine 手工重绑；两个 codec 重绑定和一个 MFD 父设备重绑定通过。第二次父设备绑定发生 NACK/读超时，后来又探测成功，可靠性仍未闭环。之后录音启停、真实暂停/恢复、原生四例和普通用户桌面双向音频回归通过。完整goal保持active。

## 源码与构建

[增量补丁](card-and-wcd-lifetime.patch)修改三文件：

- machine在link exit解除RX/TX共享jack，时点在codec component移除之前；card probe/remove复位jack_created/component。实际ASoC核心只有card进入probed生命周期才执行remove，因此新增probe入口也覆盖BE初始化失败的清理，不能仅靠晚期remove标记。
- MFD为UP/DOWN/remove建立私有互斥状态，重复通知不重复分配；子设备先移除，IRQ domain随后注销，最后regmap_exit；初始化失败逆序清理。保持原有上电值，检查所有bring-up写错误，regulator get改为devm。probe结束处理已为UP的bus device，并在尚无私有数据的早期通知返回defer，避免初始UP状态被SLIM核心的“状态未变”过滤掉。
- codec的interface regmap改由codec设备负责释放，解除映射后再归还sidev引用；logical address获取错误向上传递。嵌入codec私有内存的MCLK hw也改为codec所有，provider和hw一起回收，注册错误不再忽略。

[函数级验证](host-tests-validation.json)共73场景：machine27（含25轮重新绑定及实际ASoC probe/remove函数）、MFD36（13个失败点、20轮16线程UP/DOWN、初始UP与早期通知）、interface6、clock4。ASan/UBSan、7个故意删掉清理/入口或用错误owner的负对照通过。MFD部分添加失败按本树mfd-core回滚契约建模；这些host结果不能替代真实probe、PM和复位时序。

[V4构建](build-package-validation.json)的W=1三个改动对象零警告，checkpatch/diff check通过，完整构建只保留未改EUD的unused-function警告；770模块与132兼容，仅两个build-id不同。配置、DTB172、15个显示源保持，NGD/messaging仍168，174端口IRQ补丁保持。FAT精确回读/检查通过，只刷logdump，boot/NV回读一致。

Image V4 SHA256 `250c435567d1ed25150715b317d9ff0c498c515c84727ffde64b3680a429e5c2`，logdump V4 `cbeedef03586aae616f8c7ec9423f5667904682fa128c184b5c0b7620392acb2`。同一175的几个未部署候选原件都保留，uname-v时间沿用第一次构建，不能靠banner区分V1—V4；实际部署以分区哈希证明。首轮模板误留modules-root174，被已有目录保护拦下，未改旧模块；[失败记录](first-build-rejected.json)保留。V2增加clock owner，V3增加card probe失败清理，V4增加初始UP处理；只有V4部署。

## 实机结果及失败范围

[首启](runtime-validation.json)79.77秒：WCD/MBHC与jack绑定两次，但声卡、Phosh/Pulse自动可用，ASoC错误/WARN/Oops为0；无machine手工重绑。两份当前regmap name读取正常，boot172/logdump V4/NV通过、SD1/GPIO140保持。

[重新绑定](reprobe-validation.json)已完成的V2三例是codec两次、MFD父设备一次。每例移除对应regmap目录和mclk，旧文件句柄返回EIO，新绑定自动恢复声卡、单Pulse CARD/profile、两个regmap与一个mclk；每例再捕获48000帧。总计4个旧句柄有持久收据，读新name无Oops。此前V1第一例在恢复成功后仅等待3秒检查PCM idle，早于Pulse默认5秒，测试判据失败；后续按实际PCM关闭等待至12秒。不能把这次计时判据误判为驱动故障。

V2第四例（第二次父设备绑定）未完成：237.714秒NGD错误中断`0x82000000`，即TX_NACKED_2加TX_MSG_SENT；237.998秒MC0x60/LA0xcf读请求返回-110，WCDbring-up/probe失败。238.049秒起又有chip ID/codec/MBHC成功探测，最终声卡恢复。测试phase仍为unbound，未记录finally里的restoration-bind；因此只报告“失败之后又探测成功、当前已绑定”，不将其说成测试重试通过。原始失败日志与阶段文件保留。

这个失败有明确I/O证据，下一步核对硬复位后main/sidev logical-address缓存与物理枚举时序，不靠额外sleep或重复bind掩盖。当前MFD会拉低reset，但初始UP路径可直接读沿用的逻辑地址；这是调查线索，尚未证明因果。另需补查SLIM bus wrapper在MFD probe已返回后get_laddr失败时的enabled regulator清理，devm get引用管理不等于enable自动清理。内部slim_report_absent实现可失效地址，公开头文件尚无该声明；先按API/锁和回调顺序设计，不直接无锁改缓存字段。

[停止/暂停](capture-stop-validation.json)在超时恢复后通过8次FE16/32/48kHz录音及3次同PCM真实PAUSED/RUNNING转换，后端固定48kHz；trigger全0，WCD underflow/overflow/Port Closed新增0、mixer保持。

[原生四例](dmic0-ucm175-low24-analysis.json)左右相关0.9776/0.9983，功放关闭对照差19.53/43.25dB；[用户paplay+parecord](desktop-acoustic-validation.json)左右相关0.9389/0.9546，对同启动原生关闭参考差18.49/42.24dB，sink/source volume和mute保持，均检出编码音。

[最终](final-validation.json)1115.14秒、taint0，ASoC/WARN/Oops/MCLK/WCD端口错误0，保留上述一次NGD错误中断/读超时/bring-up超时；不能写“所有错误为0”。单CARD/alsa-card、HiFi (Mic, Speaker)，真实jack off，PCM关闭，功放37/37配平关闭静音，17控件恢复，NGD suspended，NV/persist/模块132及UCM173核验通过，MBHC/jack总计7次对应多次绑定。callaudiod继续拥有端口策略。

175通过了原172 debugfs name的当前读取和已删除文件句柄路径；修复了缺失的资源清理，但未用无限压力证明所有debugfs或SSR缺陷都消失。父设备复位/冷启动/SSR/休眠/长稳、正常音质/瞬态仍开放；用户暂无耳机，实际插拔、3/4段、耳机/耳麦/按键未验，不重复问。171的人工听音不移作175音质证据。

## 产物与续作

完整私人证据在`E:/edk2-samurai-out/kernel175/k175-all-private.tar.gz`和两个声学包，手机`/var/lib/samurai/k175*`保留初次测试判据失败、V2父设备失败及恢复。公开目录含脱敏验证、补丁和脚本。WSL内核树tracked现在7文件，多了MFD；[源码哈希](source-validation.json)与V4一致，尚未开始176修改。

回退可用完整boot172/logdump172+UCM173；boot174/logdump174候选与171人工出声SD1版本也保留。切换前重新核对当前启动和完整停机，旧175 preflash是174身份；一次F1后USB EIO不重复发。工作规则见[边界](../../WORKING-BOUNDARIES.md)，当前检查点见[NEXT-SESSION](../../NEXT-SESSION.md)。
''',encoding='utf-8')
(root/'sessions/175-card-regmap-clock-lifetimes-and-reset-nack.md').write_text('''# 175：声卡、regmap与clock生命周期及父设备复位NACK

2026-10-14。kernel175 V4/logdump175已部署，boot/DTB172、UCM173保持。新增card probe/link exit/remove清理、MFD每UP实例的逆序释放、codec-owned interface map/MCLK及初始UP处理。73场景/7负对照、W=1/完整构建和FAT回读通过。

175首启经历两次codec/MBHC绑定但声卡自动可用；codec两个重绑定、父设备一个重绑定通过，4个旧debugfs句柄EIO，mclk随codec删除/重建。第二次父设备绑定出现NGD0x82000000 NACK、MC0x60读-110，后来再探测成功；测试套件未全过。V1等待idle只有3秒的判据错误与V2真实NACK分开保存。

超时恢复后8次录音启停/3次真实暂停、原生四例和普通用户paplay+parecord左右编码检出通过。最终taint0、PCM/功放关闭、37/37配平；上述一次NACK/读/bring-up超时仍开放。实际耳机、音质、冷启动/SSR/休眠/长稳未验。

完整范围与下一步地址/复位和probe失败电源清理见[175证据](../reference/kernel175/README.md)。[174](174-port-interrupt-stop-and-card-reprobe.md)的手工machine恢复与原172 Oops历史保留；不能把175功能回归说成所有可靠性完成。
''',encoding='utf-8')
(root/'NEXT-SESSION.md').write_text('''# Realme X2 Pro 当前检查点

最后核对：2026-10-14，kernel175 V4/logdump175、boot/DTB172、UCM173。首启和codec重绑定自动恢复声卡，资源释放路径、停止/暂停与左右声道回归通过；第二次父设备硬复位绑定出现NACK/-110，后来再探测恢复，可靠性未闭环。完整音频goal active。用户暂无耳机，不重复问。规则见[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)。

## 最后核对的部署与范围

| 项目 | 结果 |
| --- | --- |
| 组合 | kernel175 V4/logdump175，boot/DTB172，modules/software132，Mesa149，UCM173；175仅刷logdump |
| 身份 | 按uname-v构建号和分区哈希；175几个未部署候选同banner，实际V4 logdump哈希cbeedef03586aae616f8c7ec9423f5667904682fa128c184b5c0b7620392acb2；私人175包/手机k175-final属于当前启动 |
| 175现场 | 1115.14秒taint0，单CARD/alsa-card，HiFi (Mic, Speaker)，真实jack off，PCM关闭，功放37/37配平关闭静音，17控件恢复、NGD suspended，NV/persist/模块132/UCM173保持 |
| 新修复范围 | card probe/link exit/remove管理jack；MFD UP/DOWN/remove释放子设备/IRQ/map；codec拥有interface map/MCLK。首启两次绑定自动成功，两个codec/一个父设备重绑通过，4个旧debugfs句柄EIO；当前name读取无Oops |
| 音频回归 | 8次录音启停、3次真实暂停恢复，WCD under/overflow/Port Closed0；原生四例与用户paplay+parecord左右编码检出、volume/mute保持。73函数级场景/7负对照通过 |
| 175未修复 | 第二次父设备bind超时：NGD0x82000000 NACK+TX_SENT、MC0x60 LA0xcf读-110、bring-up失败各1次；后来又成功probe，测试没有restoration-bind收据。不能写所有错误0或四例重绑全过 |
| 端口策略 | callaudiod主动卸载Pulse端口切换模块并接管选择，缺模块不是加载故障。UCM默认profile自动恢复，实物耳机事件未验 |
| 显示/GPU | 165实屏/DPMS与147/149修复范围保持；175显示源保持163。冷启动/休眠/长期仍开放 |

依据：[175](reference/kernel175/README.md)、[174](reference/kernel174/README.md)、[173](reference/kernel173/README.md)、[172](reference/kernel172/README.md)、[171人工听音](reference/kernel171/README.md)、[168](reference/kernel168/README.md)、[165显示](reference/kernel165/README.md)。其它功能见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。171“两组都听到，来自手机”不算175音质验收。

## 源码、产物与回退依据

- WSL `/home/cy122/pmos-samurai-kernel136/kernel` tracked现在7文件：DTS、NGD、messaging、MFD WCD、codec WCD、公共MBHC、machine。175改三个生命周期源，174端口IRQ保持；NGD/messaging168、DTS/MBHC172、15显示源163。[V4哈希](reference/kernel175/build-package-validation.json)。尚无176修改。
- 175 V1模板module目录保护失败未改旧模块；V2/V3均未部署，只有V4部署。原件/日志保留，同uname时间不能区分候选。770模块132兼容，DTB/固件172保持。EDK2 BDS源码164、生成Build固件172、FdtBlob恢复旧129；工作区不是pristine132。
- 回退完整boot172/logdump172+UCM173；174候选及171 SD1人工版本保留，更早164/168是SD0，161/166拒收不混入验收。UCM源linux-port/ucm2、scripts/samurai-audio-route.py和三文件安装器保持；UCM132原件在k173-source/私人173包，回退检查唯一alsa-card子模块。
- Mesa149和[0015补丁](linux-port/patches/0015-mesa-turnip-a640-vm-bind-iova-alignment.patch)保持，普通包更新/旧rootfs132可能覆盖；150降级未部署。

## 续作与已知风险

1. 先核对当前设备、源码/产物及边界，goal继续；175 preflash属于旧174 boot，不可作新切换身份。
2. 优先修父设备reset后NACK/-110。已知失败是MC0x60读、TX_NACKED_2；调查main/sidev在reset后沿用缓存logical address及枚举时序，因果未证明，不加sleep/循环bind掩盖。MFD初始UP在core重复状态过滤前主动初始化，可能早读旧地址；核对锁/API和重新查询。slim_report_absent实现已export但仅内部头声明，勿直接无锁改缓存。
3. 补查SLIM bus wrapper在MFD probe返回之后get_laddr失败的enabled regulator清理；devm get引用管理不等于enable自动清理。随后实测反复reset/正常启动、SSR/休眠，再做音质/瞬态和实物耳机。有耳机再验3/4段、插拔/自动profile、声道/耳麦/按钮。见[AUDIO-NEXT-SESSION-PROMPT](AUDIO-NEXT-SESSION-PROMPT.txt)。
4. 原172 debugfs name Oops历史保留，175通过当前name和删除旧句柄路径，不扩大为所有debugfs缺陷消失。V1重绑3秒idle判据早于Pulse5秒，V2改按真实PCM关闭最多12秒；V2父设备超时是独立真故障。
5. 显示停机fbdev last-close曾恢复CRTC；工具只当前启动关闭fbdev_emulation/null modeset，再检查fd关闭后的inactive状态。新启动参数Y；一次F1后USB EIO不重发。其余电池/摄像头/传感器/蜂窝/GNSS/外围和整机可靠性按硬件清单继续。165旧启动记录器已停止，DPMS用DisplayConfig.PowerSaveMode。

历史见[会话索引](sessions/INDEX.md)、[显示修复](sessions/display-handoff-152-165.md)，维护见[文档导航](DOCS-INDEX.md)。私人身份、密钥、录音及原始日志不发布。
''',encoding='utf-8')
(root/'AUDIO-NEXT-SESSION-PROMPT.txt').write_text('''在 E:\\RealmeX2Pro edk2 继续原生Linux音频修复/实机验收，goal active。先读 NEXT-SESSION.md、WORKING-BOUNDARIES、HARDWARE-STATUS、reference/kernel175/README.md，再查174/173/172/171/168。

当前kernel175 V4/logdump175，boot/DTB172、modules/software132、Mesa149、UCM173。175几份未部署候选同banner，按V4分区哈希cbeedef03586aae616f8c7ec9423f5667904682fa128c184b5c0b7620392acb2确认。当前身份在私人175/k175-all-private.tar.gz和手机k175-final；preflash是旧174启动。WSL kernel136 tracked7文件，175改machine/MFD/codec；其它哈希见V4审计，尚未开始176。

175 card probe标记生命周期使BE失败也能remove，link exit在codec有效时解除共享jack，remove复位标记。MFD私有锁/idempotent UP、逆序children/IRQ/map清理；所有bring-up IO检查，regulator get devm。codec interface map归codec、exit后put sidev；MCLK hw/provider同属codec，错误向上返回。初始UP主动初始化，早期dataNULL通知defer。73函数场景/7负对照、ASan/UBSan、实际ASoC core gate、W=1/完整构建、770模块兼容和FAT回读通过，只有V4部署，175V1模板目录保护失败原件保留。

175首启MBHC/jack两次但card自动恢复，不用machine手工重绑。V2两个codec+一个MFD父设备重绑成功，4旧debugfs句柄EIO，mclk删除再创建、每例48000帧。V1初次3秒idle判据早于Pulse5秒，保留后改等待最多12秒。

V2第四例/第二次父设备bind真失败：237.714 NGD0x82000000(TX_NACKED_2+TX_SENT)，237.998 MC0x60 LA0xcf读-110/bring-up失败，238.049又probe成功。phase仍unbound，无finally restoration-bind收据，当前已绑定。不要说四例全过。优先查reset后main+sidev logical-address缓存/枚举，初始UP可早读旧地址，这是线索未证明；不以sleep/循环bind代修复。slim_report_absent已export但仅内部头声明，按API与ctrl锁/状态回调设计。另查MFD probe返回后SLIM wrapper get_laddr失败时enabled regulator清理，devm get不自动disable。

超时恢复后8次录音启停、3次真实pause通过。原生四例左右corr .9776/.9983、关闭功放差19.53/43.25dB；用户paplay+parecord corr .9389/.9546、差18.49/42.24dB。最终1115.14秒taint0，ASoC/WARN/Oops/MCLK/端口错误0，但上述NACK/读/bring-up各1必须保留；单CARD/alsa-card，HiFi(Mic,Speaker)，jack off，PCM关、功放37/37配平关闭、17控件恢复、NGD suspended、NV/persist/模块132/UCM核验，MBHC/jack共7。录音私人，无175人工音质确认。

原172读name Oops不重写历史；175当前name/已删除句柄路径验证无Oops，不扩大所有debugfs/SSR修复。用户暂无耳机，不重复问；剩余父设备reset、正常启动/SSR/休眠/长稳、音质/瞬态、实物插拔/耳麦/按钮。callaudiod主动卸载module-switch-on-port-available并拥有端口选择，勿为缺模块强制补载。UCM源/三文件安装器保持。

回退完整boot172/logdump172+UCM173，171 SD1人工版保留，164/168是SD0。UCM132原件在k173-source/私人173包，回退核验唯一子模块。切换前取新身份和完整停机；F1后USB EIO不重发。fbdev_emulation仅停机启动临时N，新启动Y，DRM关fd后复核inactive。保护NV/校准与私人数据，不绕保护盲增功放，蓝牙只扫描不连接，振动不加脉冲。
''',encoding='utf-8')
p=root/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text();a=s.index('用途：');b=s.index('\n\n**',a)
s=s[:a]+'''用途：当前硬件验收清单。最后核对：2026-10-14，kernel175 V4/logdump175、boot/DTB172、software/modules132加Mesa149/UCM173。175首启自动声卡和codec生命周期、停流/暂停/左右声道回归通过；第二次MFD父设备reset出现NACK/-110，可靠性开放。显示实屏证据属165。以[音频175](../../reference/kernel175/README.md)、[174](../../reference/kernel174/README.md)、[171人工听音](../../reference/kernel171/README.md)、[显示165](../../reference/kernel165/README.md)、[GPU149](../../reference/kernel149/README.md)为准；规则见[WORKING-BOUNDARIES](../../WORKING-BOUNDARIES.md)。'''+s[b:]
lines=s.splitlines(True)
for i,line in enumerate(lines):
    if line.startswith('| 音频 |'):lines[i]='| 音频 | 171人工双组滴声；172偏置和UCM173数字耳机路由；175首启重探测自动card恢复、两个codec/一个父设备重新绑定、4旧debugfs句柄EIO、MCLK回收；8录音/3暂停、原生及用户双向左右检出，taint0、PCM/功放关闭 | 第二次父设备reset绑定NACK/读-110，后来probe恢复但可靠性未修复；查逻辑地址/枚举与probe失败电源清理。用户暂无耳机，实物插拔/profile/声道/耳麦/按钮未验；音质/瞬态、声学保护、冷启动/SSR/休眠及长稳开放，不将局部debugfs验证扩大 |\n'
p.write_text(''.join(lines),encoding='utf-8')
assert (root/'NEXT-SESSION.md').stat().st_size<=6500
assert (root/'AUDIO-NEXT-SESSION-PROMPT.txt').stat().st_size<=4000
print('K175_DOCS_SOURCE_AND_DEPLOYMENT_CHECKPOINT_WRITTEN',flush=True)
