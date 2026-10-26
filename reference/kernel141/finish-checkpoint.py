from pathlib import Path
import hashlib
import json
import re
import tarfile

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel141'
out = Path('/mnt/e/edk2-samurai-out/kernel141')
with tarfile.open(out / 'settled-health-private.tar.gz') as archive:
    data = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
assert data['boot-id-private.txt'] == (out / 'embedded-boot-id-private.txt').read_bytes()
health = json.loads(data['health-validation.json'])
assert health['stage'] == 141 and health['current_kernel'] == 140
assert health['same_boot'] and health['taint_values'] == [0] and health['counters_unchanged']
assert health['desktop_pids_unchanged'] and health['phosh_present_final'] and health['phoc_present_final']
health['archive_hash_verified'] = True
(ref / 'settled-health-validation.json').write_text(json.dumps(health, indent=2) + '\n')
runtime = json.loads((ref / 'first-runtime-validation.json').read_text())
assert runtime['new_boot_verified'] and runtime['boot132_and_logdump140_readback_exact']
assert runtime['all_770_modules_verified'] and runtime['persist_preserved'] and runtime['gpt18_preserved']
runtime['gpu_probe_allowed'] = False
runtime['gpu_probe_policy_reason'] = 'Known unresolved standalone136 delayed CCU faults; ordinary desktop trace is separate evidence.'
runtime['final_health_record'] = 'settled-health-validation.json'
(ref / 'first-runtime-validation.json').write_text(json.dumps(runtime, indent=2) + '\n')
startup = json.loads((ref / 'reboot140-startup-validation.json').read_text())
early = json.loads((ref / 'early-startup-validation.json').read_text())
findings = json.loads((ref / 'new-boot-findings-validation.json').read_text())
assert startup['trace_loss_free'] and startup['own_trace_timeout_events'] == 2
assert early['early_default_loss_free'] and early['early_timeout_events'] == 1
assert findings['tx_first_failure']['channel'] == 0 and findings['state_3_means_controller_DOWN']
counts = health['counts_after']
summary = (f"阶段141实际仍为#140/software132，普通亮屏53.835秒观察无新增错误；同一内核受控重启一次、未写分区。"
           f"新启动86.699秒追踪保留两次显示超时完整窗口、无丢失，帧完成回调在91.018/95.291ms到达，83ms看门狗保持。"
           f"桌面1869次GPU提交/刷新/退休对应、无fault，不能替代136专项迟发CCU故障的验收。"
           f"首次TX诊断确认state=DOWN且channel为空，前有PDR监听超时和SSR唤醒失败；BAM分配失败/挂起拒绝诊断未出现。"
           f"实际boot/logdump/liveDT/GPT18/persist/770模块及来源全通过；随后{health['elapsed_seconds']}秒8次观察桌面PID、taint0及计数不变，"
           f"累计DPU{counts['dpu_timeouts']}/DSI{counts['dsi_errors']}/GPU{counts['gpu_faults']}/WARN{counts['warnings']}/TXprepare{counts['tx_dma_errors']}。"
           "显示、GPU、充电与完整系统目标仍active。")
session = root / 'sessions/141-normal-wake-and-loss-free-startup-display-trace.md'
assert not session.exists()
session.write_text('''# 阶段141：普通亮屏和新启动显示追踪

2026-10-12。''' + summary + '''

旧140 boot的四次显示timeout与默认trace逐一对应，但CPU0/1/2有overrun，只用于有证据的时序，不由事件缺失推断没有中断。旧boot同函数trace紧邻错误打印的四对偏移约2.856921秒，范围仅该boot；不能移用到136或本次新boot。一次普通wlr-randr亮屏中4次PP帧完成为14–26ms，5次桌面GPU submit/flush/retired对应，53.835秒计数不变。该测试没有独立GPU benchmark，不证明专项CCU根因修复，也未取得实际像素可见性确认。

完整140来源/分区审计、GUI/DRM/PCM/功放/三个远端排空、freeze/F1各一次，然后fastboot仅reboot。同一#140版本号不能证明新启动，已另验真实boot标识改变。没有构建141内核或写boot/logdump/userdata。当前真实身份以私有kernel141/embedded-boot-id-private.txt、phone k141-first-runtime为准；kernel141/source-boot-id为重启前的旧140，kernel140/embedded-boot-id也已成为历史。

新boot59.33秒起的独立8192KiB/CPU实例持续86.699秒，8CPU的overrun/commit overrun/dropped均0；最后Phosh/Phoc稳定，实例已禁用移除。1182次kickoff及PP完成对应，1869次普通桌面GPU提交均退休；正常看门狗完成中位16.437ms，两次超时对应91.018ms和95.291ms的迟到PP回调，期间没有新的kickoff，资源状态ON。回调晚到不证明是假超时；现有trace没有IRQ entry/exit、CPU idle和完整硬件TE边沿，下一项需补充它们区分中断延迟/硬件停帧。默认early实例虽未overrun且有最初一次timeout，但第一条已是timeout，缺其前置arm，不能说三个超时都有完整前因。

首次TX diagnostic为state3/qmi1/channel0/device0/sg0/config_sg0/len8。源码枚举证明3是DOWN；前有两次PDR listener -110和HW wakeup attempt during SSR。之后9次prepare失败，稍后codec再次探测成功；139未提交资源回收保持，没有ENOSPC。此次不是BAM malloc失败或已证明EBUSY挂起链，不改GFP。runtime_resume会丢弃power_up的错误是真实代码缺陷候选，但直接return ret可能让runtime PM保留错误、阻止下次QMI UP恢复；先核查恢复语义和实际函数测试，再决定补丁。尚未应用该修改。

用户询问搜索线索后核对了上游DPU空闲timer竞态讨论、SLIMbus error-path提案、Mesa Freedreno缓存说明和MPS MP2650官方产品说明。DPU讨论的busy已清零条件不等于当前busy1；SLIMbus提案作者只做编译测试，本地139已有12项实际函数注入和实机恢复证据；Mesa CCU资料支持检查图像回写/缓存/映射方向，不等于现成修复；MP2650支持buck或boost和2–4节，不能由USB5V直接判为不能充电。来源和适用范围见reference/kernel141/internet-leads.md。

充电仍只有观测链和138只读阈值证据，当前132没有134输入额度驱动；恢复阈值8.525V、目标8.725V不能替代保护、温度、失联和持续充电验收。后续被动8次观察无计数/PID增长，但累计3个DPU和9个TX错误保持，因此仍不满足无报错目标。

所有raw日志、地址、PID、boot标识、来源、镜像在E:/edk2-samurai-out/kernel141与phone /var/lib/samurai/k141-*。141一次性动作已终态，下一次诊断使用新阶段/新前缀和当前真实boot审计，不重放141。

证据：reference/kernel141/normal-wake-validation.json、reboot140-startup-validation.json、early-startup-validation.json、new-boot-findings-validation.json、first-runtime-validation.json、settled-health-validation.json。既有功能回收见[139](139-slimbus-unsubmitted-tx-unwind-and-live-boot.md)，GPU故障见[136](136-legacy-gpu-vm-trace-and-ccu-address-correlation.md)，充电见[138](138-readonly-charger-recharge-threshold.md)。
''')
(root / 'NEXT-SESSION.md').write_text('''# Realme X2 Pro继续检查点（阶段141，2026-10-12）

''' + summary + '''

先读[阶段141](sessions/141-normal-wake-and-loss-free-startup-display-trace.md)及reference/kernel141/new-boot-findings-validation.json、reboot140-startup-validation.json、settled-health-validation.json。当前实际#140/release k132，完整rootfs132936包/770模块保持。身份只用私有kernel141/embedded-boot-id-private.txt或phone k141-first-runtime。141/source-boot-id、140/embedded-boot-id已是旧boot。141普通亮屏、quiesce、EUD enable、freeze/F1、fastboot reboot、启动trace全部终态，不重放；两次实例均移除，桌面正常、taint0、累计DPU3/DSI0/GPU0/WARN0/TXprepare9。

下一项显示：83ms期限下PP回调在91–95ms到达。现有两次完整窗口资源状态ON、没有介入kickoff，正常中位16.437ms；补录IRQ entry/exit、CPU idle/frequency和PM事件，明确CPU0中断延迟还是硬件TE/帧停顿。使用新阶段142和独立前缀，当前内核即可增加事件，不需因诊断而修改面板/看门狗或刷分区。第一次timeout只有early事件，无前置arm，不夸大覆盖。

NGD新证据：DOWN/channel NULL之前有PDR listener -110和SSR wake failure，旧EBUSY只是代码候选，没有本次诊断支持。runtime_resume丢弃power_up错误；直接传播会影响PM runtime_error与QMI UP恢复，先检查PM源码和函数注入，不部署已知可能阻断恢复的一行修改。139队列/TID/PM回收修复已保留。

C上的/home/cy122/pmos-samurai-kernel136/kernel仍为#140源码/Image，未做141内核编辑。modules-root140770件和稳定132四件套/136/137/139/140私有快照保持，复用树避免复制4GiB。E118卷上次140已干净关闭；访问同一WSL调用先ensure，原C WSL VHD不动。

GPU136两次CCU READ TRANSLATION仍未修。当前1869次仅普通桌面，禁止视作专项通过或重放旧33场景。充电138只读24交易已终态，8.525V恢复阈值及termination保持，不等于保护和持续控制；无134 USB额度驱动，userdata未全量刷。私人标识、地址、凭据、固件和raw镜像不公开。蓝牙不配对、振动不新脉冲、不提交推送；完整系统goal active。
''')
for name, link in [('README.md', 'sessions/141-normal-wake-and-loss-free-startup-display-trace.md'),
                   ('linux-port/README.md', '../sessions/141-normal-wake-and-loss-free-startup-display-trace.md'),
                   ('linux-port/docs/HARDWARE-STATUS.md', '../../sessions/141-normal-wake-and-loss-free-startup-display-trace.md')]:
    path = root / name
    text = path.read_text()
    position = text.index('\n') + 1
    path.write_text(text[:position] + '\n最新阶段141：' + summary + '\n\n详见[阶段141](' + link + ')。以下为此前历史。\n' + text[position:])
path = root / 'DOCS-INDEX.md'
text = path.read_text()
position = text.index('\n') + 1
path.write_text(text[:position] + '\n- [阶段141：普通亮屏和新启动显示追踪](sessions/141-normal-wake-and-loss-free-startup-display-trace.md)\n' + text[position:])
for path in [session, root / 'NEXT-SESSION.md']:
    assert all(link.startswith('https:') or (path.parent / link).is_file() for link in re.findall(r'\]\(([^)]+)\)', path.read_text()))
assert not any(re.search(r'\b[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}\b', path.read_text()) for path in ref.iterdir() if path.is_file())
(ref / 'documentation-validation.json').write_text(json.dumps(dict(stage=141, current_kernel=140,
    new_boot_runtime_audited=True, settled_health_archive_verified=True, links_verified=True,
    private_uuid_absent=True, all_three_functions_acceptance_pending=True, goal_complete=False), indent=2) + '\n')
print('K141_NEW_BOOT_RUNTIME_AND_FINDINGS_CHECKPOINT_WRITTEN')
