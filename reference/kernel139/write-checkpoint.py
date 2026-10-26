from pathlib import Path
import json

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel139'
health = json.loads((ref / 'first-health-validation.json').read_text())
assert health['current_kernel'] == 139 and health['archive_hash_verified']
session = r / 'sessions/139-slimbus-unsubmitted-tx-unwind-and-live-boot.md'
assert not session.exists()
session.write_text('''# 阶段139：SLIMbus未提交发送回收与实际启动

2026-10-12。从稳定132源码复用C侧构建存储，只改NGD和messaging两文件；136追踪和137 MFD/诊断增量恢复为132原字节，先封存137全部差异。NGD把预留槽位放到用户事务号分配后，在tx_lock内预留、组包、提交。prepare返回NULL时清completion并回退最新tail；不推进head，不回收已提交超时槽位。未提交的core/转换user事务释放TID并置零，直接user调用者维持原有TID所有权。messaging初始化TID提前，TID分配失败经过PM错误回收。DMA分配策略、GPU命令、显示和充电配置未改。

故障注入提取实际驱动5个函数与2个判定函数，宿主仅替换DMA/TID/锁/PM原语。原132连续prepare失败31次后队列耗尽，随后69次ENOMEM；139连续失败100次无耗尽，下一次有效发送及载荷正确。12项涵盖TID/PM回收、满队列、早期状态失败、转换user、直接user所有权以及较早在途槽位。地址/未定义行为检查无诊断。这证明错误回收逻辑，不等于实际DMA时序、首NULL原因或整机验收。

[上游同类槽位讨论](https://lkml.iu.edu/2609.2/05810.html)的作者确认[仅编译验证](https://lkml.iu.edu/2610.0/02660.html)；本地采用串行预留后回退tail，避免把较早在途head当未提交槽位释放。TID分配的PM回收与[已提出的修复](https://lkml.iu.edu/2609.2/04989.html)一致。没有提交、签名或声称上游已合入。

W=1对象和完整Image/770模块/DTB构建、depmod、增量checkpatch均无警告错误。全树diff检查发现继承132的eud_earlycon两处空白，保留原记录；本次两文件diff检查通过。770模块、DTB及initramfs蓝牙模块与132原字节一致。四件套重新全hash、FAT精确读回/fsck通过；boot及完整rootfs132保留，只刷logdump。服务/DRM/PCM/功放/远端/追踪先排空，freeze一次/F1一次，无userdata全量刷写。

实际#139/release k132 boot、logdump、liveDT、GPT18、persist、770模块、NV6/来源4/vendor1及桌面3配置校验通过。初始PID尚未启动，稍后Phosh/Phoc自主恢复；8次28.692秒被动观察PID不变、taint0，累计DPU2/DSI0/GPU0/WARN0/TX prepare70全部不变。70次prepare失败在26.612342–48.586130秒，未出现Message buffer unavailable或TX timeout，之后codec再次完成探测；符合回收后队列未耗尽，但首NULL原因未证明。不得因无WARN或桌面恢复宣称无报错。

当前保留#139/software132，完整rootfs936包/770模块，所有139一次性部署终态，不重放。GPU136的延迟CCU fault仍开放；139未施加GPU负载。充电仍是只读MP2650观测，138确认2S目标8.725V/恢复阈值8.525V和termination，不等于控制/保护验收。

下一定位：runtime_suspend在QMI拒绝前已清DMA channel，而EBUSY返回时PM维持active、状态未进入ASLEEP，代码上可造成后续prepare的channel空。尚未有本boot参数/返回值证明，不凭假设改DMA分配标志。当前KPROBES/FUNCTION_TRACER关闭，不能伪称已捕获动态参数；需要独立首次失败及suspend拒绝诊断。

证据：reference/kernel139/unwind-source-validation.json、host-fault-injection-validation.json、source-check-validation.json、unwind-build-package-validation.json、first-runtime-validation.json、first-health-validation.json。原始PID、地址、boot身份、日志、镜像留E:/edk2-samurai-out/kernel139与phone /var/lib/samurai/k139-*。
''')
intro = '''阶段139实际加载#139/software132，NGD未提交DMA失败的槽位/completion/TID与PM回收已修；从132只改两SLIMbus文件，136/137增量撤出候选。实际函数宿主注入12项通过：原31次失败耗尽，修复后100次失败仍可继续有效发送；较早在途槽位与直接user所有权保持。770模块/DTB原字节、四件套及实际boot/liveDT/GPT18/persist/NV来源全部通过，只刷logdump。桌面自主恢复，28.692秒8次PID/taint0/错误计数不变；累计DPU2/DSI0/GPU0/WARN0/TX prepare70，仍不是无报错或整机验收。70次启动期prepare失败后codec再完成探测、未出现队列满/发送超时，但首NULL原因未证明。当前rootfs132936包/770模块不变，无134 USB额度驱动；GPU延迟CCU/显示启动timeout/充电控制保护仍待办。完整系统goal active。'''
next_text = '''# Realme X2 Pro继续检查点（阶段139，2026-10-12）

''' + intro + '''

先读[阶段139](sessions/139-slimbus-unsubmitted-tx-unwind-and-live-boot.md)、[阶段136](sessions/136-legacy-gpu-vm-trace-and-ccu-address-correlation.md)、[阶段138](sessions/138-readonly-charger-recharge-threshold.md)及reference/kernel139/first-health-validation.json。当前真实#139/release k132，身份只用私有kernel139/embedded-boot-id-private.txt或phone k139-first-runtime；kernel139/source-boot-id是旧132，kernel137/embedded是旧132，都不是当前。139所有一次性部署已终态，不重放。

下一定位：NGD runtime_suspend先exit_dma后请求QMI，EBUSY时PM留active而DMA空；这只是源代码候选，未捕获当前NULL参数。当前KPROBES/FUNCTION_TRACER关闭；应在139上加入首次NULL与首次suspend拒绝诊断，保留既有回收逻辑，不混入137 MFD、不盲改GFP_NOWAIT。暂不运行GPU负载。GPU地址需按TTBR匹配，跨时钟顺序未证明；不盲改HBB、缓存或对齐。充电138数据24次读取终态不重放。

C上的/home/cy122/pmos-samurai-kernel136/kernel现为#139源码/构建，目录名不代表版本。136/137 before diff、各Image和稳定132完整四件套已私有封存；模块树modules-root139完整770件。E118/power132源未动，访问同一WSL调用先ensure。继续复用C树前封存139，不再复制4GiB。原C WSL VHD不动。

保护/校准/身份/NV/vendor、Android和数据保持；私人标识/地址/凭据/raw日志/镜像仅在E:/edk2-samurai-out和phone /var/lib/samurai。长错留档换项，蓝牙不配对、振动不新脉冲、不提交推送，不全量刷userdata。显示、GPU、充电与15组完整系统目标均未完成。
'''
(r / 'NEXT-SESSION.md').write_text(next_text)
for name in ['README.md', 'linux-port/README.md', 'linux-port/docs/HARDWARE-STATUS.md']:
    p = r / name
    t = p.read_text()
    pos = t.index('\n') + 1
    p.write_text(t[:pos] + '\n最新阶段139：' + intro + '\n\n详见' + ('[阶段139](sessions/139-slimbus-unsubmitted-tx-unwind-and-live-boot.md)' if name == 'README.md' else '[阶段139](' + ('../' if name == 'linux-port/README.md' else '../../') + 'sessions/139-slimbus-unsubmitted-tx-unwind-and-live-boot.md)') + '。以下保留此前历史。\n' + t[pos:])
p = r / 'DOCS-INDEX.md'
t = p.read_text(); pos = t.index('\n') + 1
p.write_text(t[:pos] + '\n- [阶段139：未提交TX回收与实际启动](sessions/139-slimbus-unsubmitted-tx-unwind-and-live-boot.md)\n' + t[pos:])
print('K139_CURRENT_BOOT_AND_LIMITATIONS_CHECKPOINT_WRITTEN')
