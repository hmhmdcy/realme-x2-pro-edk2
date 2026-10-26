from pathlib import Path
import json

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel138'
current = json.loads((r / 'reference/kernel137/rollback-runtime-validation.json').read_text())
health = json.loads((r / 'reference/kernel137/rollback-health-validation.json').read_text())
charge = json.loads((ref / 'charge-threshold-validation.json').read_text())
assert current['new_boot_verified'] and current['kernel_build'] == 132 and current['taint'] == 0
assert health['phosh_present_final'] and health['phoc_present_final'] and health['counters_unchanged']
assert charge['configuration_data_writes'] == 0 and charge['source_vendor_package_hashes_passed']
summary = ('阶段136已构建/部署默认关闭的GPU legacy VM映射与切换追踪，固定800×600像素单项通过但仍两次CCU READ TRANSLATION。故障页表内44次映射操作不覆盖故障地址，7个转储BO均精确匹配自身映射；故障比最近颜色BO低32KiB，不能由另一页表数值地址相同推断跨进程访问或释放后使用。离线估计停在CCU resolve/提交收尾，非根因；OEM与当前A640的UBWC3/HBB15契约相符，未改GPU命令、全局debug、缓存刷新或分配对齐。阶段137补入上游WCD934x资源清理和首次DMA失败诊断，770模块/DTB原字节及四件套验证通过并实际只刷logdump。该boot无WCD/DMA告警、taint0，却大量DSI FIFO/MDP下溢和DPU3，候选拒绝，不能证明音频根因已修。已排空服务、freeze/F1各一次并只刷logdump回退#132，boot/logdump/liveDT/GPT18/persist/770模块/11来源全通过；桌面自主恢复，28.692秒8次守卫PID/taint0及计数不变，累计DPU3/DSI0/GPU0/WARN0/DMA0，仍未验收持续显示或整体GPU。阶段138只读24次寄存器交易并恢复同一MP2650观测客户端，配置与133全相同；原厂DT及REG07均2节，REG04=68得到整包目标8.725V/恢复阈值8.525V，实际8.624→8.547V仍高于恢复阈值、REG13为charge termination；零或小电流不证明充电故障，也不证明充电控制完成。当前仍为匹配rootfs132、无134 USB额度驱动；保护链、失联行为与持续充电控制待办，userdata未全量刷入。15组与完整系统goal active。')
sessions = {
 '136-legacy-gpu-vm-trace-and-ccu-address-correlation.md': '''# 阶段136：legacy GPU VM追踪与CCU地址核对

2026-10-12。以稳定132软件构建#136，新增msm_gpu_vm_update和msm_gpu_vm_switch_enqueue，默认关闭；不改GPU命令、全局debug、缓存策略或分配对齐。Image、770个模块、DTB、initramfs和完整rootfs四件套验证，实际只替换logdump。

首boot有31次SLIM TX DMA prepare失败与WCD934x efuse WARN（taint512），Phosh/Phoc存在。单项GPU诊断显式保留该已知告警边界，不能作为清洁运行验收。UID10000固定800×600 build场景像素Success，但退出后两次CCU READ TRANSLATION；有界70.369秒窗口桌面PID、DPU2/DSI0/WARN1保持，GPU仍失败。

追踪无丢失：24次map、23次unmap、9次页表切换、12次flush/11次retired。legacy managed VM未受旧vm_log_shift接口覆盖，先前历史未记录，不能以空记录证明映射释放。

故障TTBR所属VM共44次操作，无一次覆盖故障地址。7个转储BO全部精确对应其自身成功映射，RB颜色/深度/标志基址在各自映射内；故障比最近颜色BO低32KiB。另一VM同数值IOVA仅为巧合，不证明跨VM状态、UAF或unmap。ftrace mono和dmesg时间尚未建立偏移，不直接比较两者先后。

Mesa26.2.4固定crashdec离线估计停在末尾IB的CCU resolve/cache flush及内核提交收尾；不是实际发起故障指令的证明。原厂固定提交9668fcdc的A640与当前核对均UBWC3/HBB15；PAGE_SIZE分配及XML标志基址约束不能支持凭猜测改64KiB对齐。GPU问题保持开放，所有原始转储、地址、进程和日志留E私人目录。

可复核：reference/kernel136/legacy-vm-trace-validation.json、legacy-fault-correlation.json、core-bo-vm-validation.json、resolve-bo-offset-validation.json、decoded-stop-validation.json、ubwc-source-contract-validation.json。两次诊断和部署已执行且终态，不重放。
''',
 '137-wcd-resource-cleanup-display-failure-and-rollback.md': '''# 阶段137：WCD资源清理、显示失败与132回退

2026-10-12。在已封存136源diff/镜像后复用C卷构建树，补入[上游WCD934x清理](https://lkml.rescloud.iu.edu/hypermail/linux/kernel/2603.1/03387.html)，并仅在首次NGD/BAM DMA失败时打印通道/分配状态。未改DMA分配策略、GPU命令或充电配置。W=1修改对象及完整构建无告警，checkpatch代码规则0/0，770模块及DTB与132逐字节相同，四件套完整hash/FAT精确回读通过。

实际#137/software132只刷logdump。首boot无TX prepare/WCD WARN/ENOSPC、taint0；这只是本次观测，不证明先前DMA/efuse根因。大量dsi_err_worker status=c（FIFO/MDP下溢）及status=0，3次DPU timeout；不可因无WARN而验收。初始PID快照过早为空，稍后Phosh/Phoc自主启动。BlueZ首次status未ready导致采集中断，仅补采剩余项目，分区操作未重放。被动EUD读发生EIO，失败记录保留，无重复com-up。

保存显示/clock现场后按当前boot守卫排空音频、无线、显示及追踪，freeze/F1各一次，只刷logdump回退132。新boot全量回读boot/logdump/live DT/GPT18/persist/770模块/11来源通过，taint0。28.692秒8次被动观察桌面PID保持且计数不变，DPU3/DSI0/GPU0/WARN0/TX DMA0；没有桌面重启、panel rebind、greetd标记或新GPU负载。首次回退快照PID也过早为空，以rollback-health-validation为当前桌面依据。

当前匹配rootfs132四件套已fresh hash；userdata未全量刷入。上游cleanup保留在源码/候选，137没有成为稳定镜像。下一项可修NGD未提交DMA错误留下TX槽位/TID的回收；不能擅自用GFP_ATOMIC、重试或删除WARN掩盖首错。

证据：reference/kernel137/audio-source-validation.json、audio-build-package-validation.json、first-runtime-validation.json、boot-error-validation.json、rollback-runtime-validation.json、rollback-health-validation.json、stable-build-package-validation.json。私有当前boot身份为E:/edk2-samurai-out/kernel137/embedded-boot-id-private.txt；rejected-boot-id是137旧boot，不是当前。
''',
 '138-readonly-charger-recharge-threshold.md': '''# 阶段138：本机充电恢复阈值的只读核对

2026-10-12，当前132与137回退同boot。固定已签收工具做两份12字段快照，24次I2C读，无配置数据写、fault REG14读、强制地址、new_device或保护/FET/OTG动作。同一OF观测客户端在finally恢复，解绑0.041121秒。两份配置与133全相同，包数据库、6 NV/4传感器来源/1 vendor及桌面PID不变，taint0，故障计数不增。

[原厂MP2650代码/头文件](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/power/oppo/charger_ic/oppo_mp2650.c)的固定hash重新验证，Android存档DT vbatt_num=2及REG07两节编码一致。REG04=0x68：电压code52，以3.7125V+52×12.5mV得到每节4.3625V、整包8.725V；恢复落差每节100mV，整包阈值8.525V。REG13=0x0f充电状态为termination。

两次电量计98%，27.8→27.7°C，8.624→8.547V，+1→-115mA；都尚高于名义恢复阈值。状态从Charging到Discharging，瞬时符号不能证明持续净充电；硬件Full锁存与这些读数相容。继承的电压不是推荐设置，不抬高浮充电压，不把98%停充认定为驱动故障。

当前132仍无134 USB source额度驱动；历史CDP1.5A不能作为当前预算。NTC/watchdog继承关闭、终止和12h安全计时器继承启用；保护/2719固件语义、温度链、失联行为及实际恢复充电仍待证实。[MPS官方产品](https://www.monolithicpower.com/en/mp2650.html)明确MP2650按输入/电芯数选择buck或boost；不能凭5V输入与2节电池就认定无法充电。没有控制验收。

证据：reference/kernel138/charge-threshold-validation.json。capture脚本已执行且终态，不重复解绑/交易。
'''}
for name,text in sessions.items():
    (r/'sessions'/name).write_text(text)
links = '[阶段136](sessions/136-legacy-gpu-vm-trace-and-ccu-address-correlation.md)、[阶段137](sessions/137-wcd-resource-cleanup-display-failure-and-rollback.md)、[阶段138](sessions/138-readonly-charger-recharge-threshold.md)'
t = (r/'README.md').read_text()
start = t.index('\n\n') + 2
end = t.index('阶段134已实际刷入')
(r/'README.md').write_text(t[:start]+summary+'\n\n'+links+'。下方为历史状态，以当前132回退和最新验证边界为准。\n\n'+t[end:])
t = (r/'linux-port/README.md').read_text()
start = t.index('\n\n') + 2
(r/'linux-port/README.md').write_text(t[:start]+summary+'\n\n当前交接：[NEXT-SESSION](../NEXT-SESSION.md)。下方为历史状态。\n\n'+t[start:])
t = (r/'DOCS-INDEX.md').read_text()
start = t.index('\n\n') + 2
(r/'DOCS-INDEX.md').write_text(t[:start]+'- '+links+'：GPU页表证据、WCD清理候选与显示失败回退、实际充电恢复阈值。\n\n'+t[start:])
t = (r/'linux-port/docs/HARDWARE-STATUS.md').read_text()
start = t.index('\n\n') + 2
t = t[:start]+'当前阶段138/实际内核132：已逐项验核137回退，Phosh/Phoc自主恢复、taint0，28.692秒计数保持DPU3/DSI0/GPU0。136故障映射证据与137拒绝候选详见最新session；以下功能历史不能扩展为本轮验收。充电实际恢复阈值8.525V已只读核对，完整控制仍未验收。\n\n'+t[start:]
lines = t.splitlines()
for i,line in enumerate(lines):
    if line.startswith('| GPU |'):
        lines[i] = '| GPU | 136固定800×600像素通过但两次CCU翻译fault；7 BO在自身VM，fault低于最近BO32KiB，根因未证实；当前回退132无新专项负载 | 不能由另一VM同IOVA推断UAF或跨VM使用；不重跑33场景、重放、全局debug或猜测64KiB对齐 |'
    elif line.startswith('| 充电'):
        lines[i] = '| 充电 / 电池 | MP2650持久只读观测与BQ电量计；138本机两节/目标8.725V/恢复阈值8.525V，配置未改 | 当前132无134 USB额度驱动；NTC/固件保护链/失联与持续充电控制未验收，不提高继承浮充值 |'
(r/'linux-port/docs/HARDWARE-STATUS.md').write_text('\n'.join(lines)+'\n')
(r/'NEXT-SESSION.md').write_text('# Realme X2 Pro继续检查点（阶段138，2026-10-12）\n\n'+summary+'\n\n先读'+links+'和reference/kernel137/rollback-runtime-validation.json、rollback-health-validation.json、reference/kernel138/charge-threshold-validation.json。当前真实内核#132/release k132；boot身份仅使用私有kernel137/embedded-boot-id-private.txt或phone k137-rollback132-runtime，source-boot-id是旧136、rejected是旧137，均不是当前。所有136–138一次性操作已终态，不重放。\n\n下一项：NGD未提交DMA错误应释放预留槽位、清completion/TID并使runtime PM平衡，先故障注入后独立构建/实际boot；首个prepare NULL原因仍未知，137本次音频0错误也不能证明根因已修。显示137 status=c/0现场已保存，保持源证据不屏蔽日志。GPU44映射/BO地址证据需按TTBR匹配，ftrace/dmesg跨时钟顺序未证明；不盲改HBB、缓存或对齐。\n\nC上的/home/cy122/pmos-samurai-kernel136/kernel现为#137源码/构建，已封存136 before diff/原镜像和137增量；该目录名不代表当前内核编号。modules-root与modules-root137分别770件完整，稳定132源及Image在E118/power132未改。下一构建可先封存137再复用此树，避免多复制4GiB。E118/134等卷依赖同一WSL调用先ensure；原C WSL VHD未动，不使用旧镜像源覆盖。\n\nrootfs132936包/770模块/完整镜像保留；最新rootfs134为候选，不是当前基线。完整userdata未刷。保护/校准/身份/NV/vendor、Android和数据保持；私人标识/地址/凭据/raw日志/镜像只在E:/edk2-samurai-out与phone /var/lib/samurai。长错留档换项，蓝牙不配对、振动不新脉冲、不提交推送，完整系统goal active。\n')
print('K138_PUBLIC_CURRENT_STATE_AND_FAILURE_BOUNDARIES_UPDATED', flush=True)
