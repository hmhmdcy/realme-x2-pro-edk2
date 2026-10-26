from pathlib import Path
import hashlib
import json
import re
import tarfile

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel140'
out = Path('/mnt/e/edk2-samurai-out/kernel140')
with tarfile.open(out / 'settled-health-private.tar.gz') as archive:
    data = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
assert data['boot-id-private.txt'] == (out / 'embedded-boot-id-private.txt').read_bytes()
health = json.loads(data['health-validation.json'])
health['archive_hash_verified'] = True
assert health['current_kernel'] == 140 and health['same_boot'] and health['taint_values'] == [0]
assert health['phosh_present_final'] and health['phoc_present_final']
(ref / 'settled-health-validation.json').write_text(json.dumps(health, indent=2) + '\n')
stable = health['counters_unchanged'] and health['desktop_pids_unchanged']
counts = health['counts_after']
summary = f'''当前实际#140/software132：保留139未提交TX回收，只增加首次NULL/BAM分配失败/挂起拒绝诊断，没有修改挂起顺序或GFP策略。139实际函数注入12项通过，100次失败后仍可发送，较早在途槽位与TID/PM回收保持。140四件套、770模块/DTB原字节和实际boot/logdump/liveDT/GPT18/persist/NV来源校验全通过，只刷logdump。140本次无TX DMA失败，三条诊断均未触发，不能证明根因已修。启动观察DPU1→4、桌面自主恢复；随后{health['elapsed_seconds']}秒8次被动观察，计数/PID稳定={stable}，累计DPU{counts['dpu_timeouts']}/DSI{counts['dsi_errors']}/GPU{counts['gpu_faults']}/WARN{counts['warnings']}/DMA{counts['tx_dma_errors']}，taint0。显示、GPU延迟CCU和充电控制保护仍未验收，完整系统goal active。'''
session = r / 'sessions/140-first-dma-diagnostics-and-display-startup-timeouts.md'
assert not session.exists()
session.write_text('''# 阶段140：首次DMA诊断与显示启动超时

2026-10-12。''' + summary + '''

源码候选：NGD runtime_suspend先exit_dma再请求QMI；EBUSY返回时PM仍active且状态未进入ASLEEP，代码上能留下空channel。当前KPROBES/FUNCTION_TRACER关闭。140仅加入dev_err_once/dev_info_once数值诊断；没有改MFD、挂起顺序、GFP_NOWAIT、显示/GPU命令或充电寄存器。三条诊断都未触发是本次没有相应失败，不是空channel、内存不足或EBUSY机制已被证明。既有139 host注入用于回收逻辑，不覆盖140诊断或QMI/硬件时序。

Image/W=1对象/770模块/DTB、depmod、checkpatch均无警告错误。FAT两文件精确读取和只读fsck通过；模块770与DTB字节仍与132一致，initramfs蓝牙模块相符，boot及完整rootfs132936包复用。四件套重新完整hash。当前139先完整来源/分区审计、排空服务/DRM/PCM/功放/远端/追踪，freeze/F1各一次，只刷logdump。主机外层误把USB断开后的native exit当PS脚本失败，随后核对F1=1/out=1/freeze确认后继续；没有重发请求或重放转换。

实际140 boot/目标logdump/liveDT/GPT18/persist/770模块/NV6/来源4/vendor1/桌面3配置校验全通过。第一次28.563秒观察横跨桌面启动，PID由无到有、DPU由1到4，应保留为增长记录。后续独立settled窗口只读确认当前计数与PID，不重放内核/负载/寄存器读。所有原始身份、PID、地址、dmesg、镜像与日志在E:/edk2-samurai-out/kernel140及phone /var/lib/samurai/k140-*。

当前保留140诊断内核，所有本轮一次性部署终态。不得将DMA0的一个boot视作永久修复。未运行新GPU负载；136固定800×600仍有两次延迟CCU fault，故障地址未被所属VM记录的映射覆盖，7 BO各自在有效映射内，根因开放。充电138两节/目标8.725V/恢复阈值8.525V/termination已读回，不等于持续充电与保护完成。

下一工作转回显示：保存140启动DPU timeout与encoder/DRM时序，明确fbcon→Phosh过程中首TE/帧完成及pending kickoff状态。不因启动timeout计数已稳定宣称无报错，也不重复33场景或启用全局GPU debug。NGD首次NULL/QMI拒绝诊断留在当前内核等待真实事件，避免凭猜测改DMA分配政策。

证据：reference/kernel140/dma-diagnostic-source-validation.json、dma-diagnostic-build-package-validation.json、first-runtime-validation.json、first-health-validation.json、dma-first-failure-validation.json、settled-health-validation.json。前序功能回收见[139](139-slimbus-unsubmitted-tx-unwind-and-live-boot.md)。
''')
(r / 'NEXT-SESSION.md').write_text('''# Realme X2 Pro继续检查点（阶段140，2026-10-12）

''' + summary + '''

先读[阶段140](sessions/140-first-dma-diagnostics-and-display-startup-timeouts.md)、[139](sessions/139-slimbus-unsubmitted-tx-unwind-and-live-boot.md)、[136](sessions/136-legacy-gpu-vm-trace-and-ccu-address-correlation.md)、[138](sessions/138-readonly-charger-recharge-threshold.md)及reference/kernel140/dma-first-failure-validation.json、settled-health-validation.json。当前真实140/release k132；身份只用私有kernel140/embedded-boot-id-private.txt或phone k140-first-runtime，source-boot-id为旧139。139/140一次性部署已终态，不重放。

下一项显示启动DPU超时：140首次观察1→4后桌面自主恢复，先从已封存dmesg/encoder/DRM状态建立fbcon→Phosh首TE/帧完成时序，必要时独立有界display追踪；不重复硬GPU故障，未验收持续显示。NGD先释放channel再QMI拒绝只是代码候选，140首失败诊断全部未触发，不能说已证明EBUSY；139已修未提交回收，但首NULL根因尚待真实事件，不盲改GFP。GPU136 BO/TTBR证据与跨时钟限制保持；充电138只读探测已终态。

C上的/home/cy122/pmos-samurai-kernel136/kernel现为#140源码/Image，目录名不代表版本。新增modules-root140完整770件；136/137/139 before diff和各Image、稳定132四件套已私有封存。下一复用树先封存140，避免再复制4GiB。E118/power132稳定源未改，访问需同一WSL调用先ensure。原C WSL VHD不动。

rootfs132936包/770模块保持，无134 USB额度驱动，userdata未全量刷。保护/校准/身份/NV/vendor、Android及数据保持；私人标识/地址/凭据/raw日志/镜像只在E:/edk2-samurai-out和phone /var/lib/samurai。蓝牙不配对、振动不新脉冲、不提交推送，长错留档换项。显示、GPU、充电和15组完整系统goal active。
''')
for name, link in [('README.md', 'sessions/140-first-dma-diagnostics-and-display-startup-timeouts.md'),
                   ('linux-port/README.md', '../sessions/140-first-dma-diagnostics-and-display-startup-timeouts.md'),
                   ('linux-port/docs/HARDWARE-STATUS.md', '../../sessions/140-first-dma-diagnostics-and-display-startup-timeouts.md')]:
    p = r / name
    t = p.read_text(); pos = t.index('\n') + 1
    p.write_text(t[:pos] + '\n最新阶段140：' + summary + '\n\n详见[阶段140](' + link + ')。以下为此前历史。\n' + t[pos:])
p = r / 'DOCS-INDEX.md'
t = p.read_text(); pos = t.index('\n') + 1
p.write_text(t[:pos] + '\n- [阶段140：DMA首次诊断和显示启动超时](sessions/140-first-dma-diagnostics-and-display-startup-timeouts.md)\n' + t[pos:])
for p in [session, r / 'NEXT-SESSION.md']:
    assert all(m.startswith('https:') or (p.parent / m).is_file() for m in re.findall(r'\]\(([^)]+)\)', p.read_text()))
assert not any(re.search(r'\b[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}\b', p.read_text()) for p in ref.iterdir() if p.is_file())
(ref / 'documentation-validation.json').write_text(json.dumps(dict(stage=140, links_verified=True, private_uuid_absent=True, current_state_140_verified=True, goal_complete=False), indent=2) + '\n')
print(json.dumps(health, indent=2))
print('K140_CURRENT_STATE_AND_UNRESOLVED_BOUNDARIES_CHECKPOINT_WRITTEN')
