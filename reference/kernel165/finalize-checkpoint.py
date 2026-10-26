from pathlib import Path
import hashlib, json, re

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel165'
out = Path('/mnt/e/edk2-samurai-out/kernel165')
runtime = json.loads((out / 'runtime-validation.json').read_text())
steady = json.loads((out / 'steady-validation.json').read_text())
final = json.loads((out / 'final-live-validation.json').read_text())
order = json.loads((ref / 'startup-order-validation.json').read_text())
assert runtime['boot164_readback_exact'] and runtime['logdump163_preserved'] and runtime['persist_preserved']
assert runtime['modules132_verified'] and runtime['mesa149_fix_preserved'] and runtime['taint'] == 0
assert not any(runtime['counts_after'].values())
assert steady['same_boot'] and steady['pids_preserved'] and steady['critical_counts_zero'] and steady['sample_count'] == 21 and steady['error'] is None
assert order['firmware_before_exit_callback_success_observed'] and order['wake_gate_count'] == 12
assert final['same_boot_as_accepted_second_boot'] and final['desktop_present'] and final['taint'] == 0
for name in ['steady-validation.json', 'final-live-validation.json']:
    (ref / name).write_bytes((out / name).read_bytes())
proofs = {}
for name in ['first-evidence-private.tar.gz', 'steady-private.tar.gz', 'preflash-private.tar.gz', 'quiesce-private.tar']:
    path = out / name
    proofs[name] = dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
(ref / 'evidence-archives.json').write_text(json.dumps(proofs, indent=2) + '\n')
summary = dict(stage=165, kernel_build=163, firmware_boot_stage=164, software_generation=132,
               current_combination_readback_verified=True, desktop_start_uptime=21.45,
               standard_dpms_operations=24, wake_gate_order_verified_count=12,
               firmware_reset_before_linux_exit_boot_services_success_recorded=True,
               native_dsi_stop_before_ctl_and_first_frame_tx_before_backlight_verified=True,
               all_full_boot_kernel_fault_warning_and_audio_dma_counts_zero_in_current_boot=True,
               same_boot_and_desktop_pids_preserved_for_seconds=steady['elapsed_seconds'],
               last_steady_uptime=steady['last_sample_uptime'], final_live_uptime=final['uptime_seconds'],
               temporary_startup_recorder_disabled=True, nv_persist_modules_and_mesa_preserved=True,
               physical_startup_feedback_required=True, first164_audio_warning_cause_unknown=True,
               previous157_uncommanded_reboot_cause_unknown=True, goal_complete=False,
               last_goal_tool_status_observed='blocked')
(ref / 'current-validation.json').write_text(json.dumps(summary, indent=2) + '\n')
(ref / 'README.md').write_text('''# 165：同一 boot164/kernel163 第二次启动软件验收

保持固件与内核，按新的当前身份正常停机/F2FS冻结，单次F1后核对实际bootloader，仅fastboot reboot，没有新增刷写。停机时只为退出164失败boot接受那一个已记录音频WARN；新启动仍要求零WARN和taint0。[工具范围](tools-validation.json)

新boot仍kernel163、boot164/logdump163/modules132/software132+Mesa149。Phoc19.73/Phosh21.45秒，全boot KMS/DSI/DPU/GPU/WARN/audio DMA prepare均0，taint0。boot164及logdump163真实读回、persist/NV/模块/Mesa均保持。[运行验证](runtime-validation.json)、[启动时间](boot-timing-validation.json)

UEFI保留日志再次记录BeforeExitBootServices回调Success、无ring丢失；固件在Linux开始初始化前请求GPIO6物理低，原生面板负责后续恢复。native CTRL先停再清CTL；初始PP TX done后约210微秒wait成功；24次标准DPMS无新增错误，12次实际亮屏门控均在PP TX done及ret0等待后完成，早期/电源trace无丢失。[顺序验证](startup-order-validation.json)、[电源回归](cycles-validation.json)

连续601.15秒、21次采样到uptime918.47，同boot/桌面PID保持，关键故障0、taint0，没有看到非指令重启。最终现场再次核对同一boot、桌面进程及taint0，临时启动记录器已停并退出runlevel。[稳态验证](steady-validation.json)、[最终现场](final-live-validation.json)

164首次的WCD934x WARN及917条DMA prepare失败没有在本次重启重现，原因仍未知，保留失败现场，不宣称音频已修复。157非指令重启原因也仍未知。用户已睡觉，实体edk2→Linux白屏/花屏效果尚未观察；目标没有标记完成，最后一次goal查询返回blocked。回来后需看着屏幕验收一次重启，不能把软件检查当作实体通过。[当前范围](current-validation.json)

可审查内核合并补丁基于154，含15个文件，当前源码哈希与编译163一致，逆向apply检查通过；固件164补丁属于另一个仓库。[内核补丁](kernel-display-fix-from154.patch)、[固件补丁](../kernel164/before-exit-panel-reset.patch)

完整私人启动/回归档案SHA256：`8ff3b50e321f2cb55abe2036a4274dbd252458b7944d8fc9e607f52ef27e807e`。其它私人档案只公开哈希，不公开原始日志或密钥。[归档摘要](evidence-archives.json)
''')
p = root / 'NEXT-SESSION.md'
s = p.read_text()
start = s.index('2026-10-14，')
end = s.index('\n\n## 当前实际状态', start)
s = s[:start] + '2026-10-14，165同一boot164/kernel163第二次启动软件验收及601秒观察通过，实体开机过渡仍待用户回来观察。用户已睡觉；目标未完成，最后goal查询返回blocked。操作规则只以[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)为准。' + s[end:]
start = s.index('现机暂为')
end = s.index('\n\n158首次日志', start)
s = s[:start] + '''现机为kernel163、boot164/logdump163/modules132/software132加Mesa149修复。165是同组合第二个新boot，没有新刷写；Phosh21.45秒，全boot关键显示错误/WARN/audio DMA prepare0、taint0，24次DPMS及12次首帧门控、601.15秒同boot/PID观察通过。boot/logdump真实读回及NV/persist/模块/Mesa保持；当前boot私人身份在kernel165 first-boot目录，不能使用旧preflash/source身份重放切换。[165验收](reference/kernel165/README.md)

Linux源码/主Image为163，15个显示相关文件与编译哈希相同；161 SMMU候选已撤销。EDK2 BDS源码为164候选，C/INF两文件有修改；源码树原有DTB为本地旧129文件，构建时临时使用实际132/163 DTB并恢复原文件。工作区生成固件目前是对照用的pristine132，不要当live164刷写包；真正164包在独立kernel164目录，原版boot132及logdump158/163备份保留。实际release仍7.3.0-rc6-rmx1931-samurai-k132+，必须按uname -v核对构建号，DRM按by-path解析。''' + s[end:]
s = s.replace('当前boot身份在kernel160私人first-boot目录，159或160的旧preflash身份不能用于下一切换。', '160启动身份已过期，不能用于当前切换。')
start = s.index('163只在pinctrl-sm8150.c')
end = s.index('\n\n\n## 显示修复链', start)
s = s[:start] + '''163在TLMM就绪后核对本机SOFEF03F GPIO6/active-low，逻辑1保持复位并释放GPIO占用；实际13.2707秒晚于SMMU13.1784/13.1809，不能声称注册顺序保证先于SMMU。163+boot132 Phosh19.39秒、48次DPMS与第二轮12门控、601秒稳定；最终到uptime3269.73同boot/PID及taint0。第一轮trace漏了最终恢复的第12门控，工具补等待后复测，原始记录保留。[163证据](reference/kernel163/README.md)

164改本机Linux启动的BeforeExitBootServices回调，通过TLMM协议配置GPIO6并输出低；14项普通/ASAN/UBSAN真实函数及2个负对照通过。原代码重编译全部模块与实际boot132一致，候选只变BdsDxe；设备树/BootShim/header/ramdisk/compat/尾部保持。32条配置/ELF RWX/LTO提示的4种模板在原代码重编译中重现，不是零提示构建。只刷boot164，kernel163保持。只读mmap日志记录回调Success，无ring丢失。[164证据](reference/kernel164/README.md)

164首次自动桌面却音频WARN1/DMA prepare917、taint512、Phosh35.32秒；165同组合重启后这些计数0、Phosh21.45秒，原因未证明。实体新固件启动过渡尚未观察，等待用户回来做一次可见重启验收。临时165记录器已禁用；当前数据/代码完整保存，目标未完成。''' + s[end:]
s = s.replace('158已通过三次软件启动检查和已测稳定性，实体早期开机过渡仍失败，goal保持active。', '165通过当前软件检查，160反馈的实体早期过渡故障是否被新固件修复仍待确认，目标未完成。')
p.write_text(s)
(root / 'NEXT-SESSION-PROMPT.md').write_text('''继续Realme X2 Pro显示BUG收尾。用户睡觉期间已完成165软件验收，目标未完成，最后get_goal返回blocked，不要创建新目标绕过状态。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel163至165/README.md。用户160确认158唤醒无闪屏、开机变快，但edk2消失后到首个Linux命令行前仍白屏花屏。

当前真实组合kernel163+boot164/logdump163/modules132/software132+Mesa149。165是同组合第二次启动，无新刷写：Phosh21.45秒、全boot KMS/DSI/DPU/GPU/WARN/audio DMA prepare0、taint0，24次DPMS/12次TX后门控、601.15秒同boot/PID及最终现场通过，受保护内容读回相同。临时165启动记录器已停并退出boot runlevel。UEFI保留日志的BeforeExitBootServices回调Success证明固件复位请求执行；原生面板首帧后亮屏，实体效果尚未观察。用户回来后首先协调看着屏幕重启验收，不重复不必要刷写。

163 TLMM注册早但实际probe13.2707晚于SMMU13.18，所以只保护较晚窗口；164进一步在UEFI离开Boot Services前配置本机GPIO6物理低，只有BdsDxe变化、DTB及其它模块与boot132一致。Linux源码/Image163，EDK2 C/INF源码164；源码树旧DTB129被临时替换为实际132/163 DTB构建后恢复，工作区生成固件是pristine132对照，不能当live164包用。独立kernel164包和原boot132、logdump158/163备份完整。15文件合并内核补丁在kernel165，逆向apply检查通过。164首次出现WCD934x WARN1/DMA917，165未重现，原因未知；161空RMR候选已拒收撤销，157非指令重启原因仍未知。新切换必须读取当前实际身份，不使用旧preflash/source收据。其它硬件开放项保持真实。
''')
p = root / 'DOCS-INDEX.md'
s = p.read_text()
start = s.index('当前进展与交接：')
end = s.index('\n\n', start)
s = s[:start] + '当前进展与交接：[163内核复位](reference/kernel163/README.md)、[164固件复位](reference/kernel164/README.md)、[165同组合复测](reference/kernel165/README.md)、[当前检查点](NEXT-SESSION.md)、[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。当前kernel163+boot164，Phosh21.45秒、关键错误0、24次DPMS/12次首帧门控/601秒稳态通过，受保护内容保持。UEFI回调实际Success，实体开机白屏是否消失待用户回来确认；首次164音频WARN未在165重现，原因未知。目标未完成。' + s[end:]
p.write_text(s)
p = root / 'linux-port/docs/HARDWARE-STATUS.md'
s = p.read_text().replace('2026-10-13，阶段159第二次158启动及稳态观察完成。已部署内核158', '2026-10-14，阶段165同boot164/kernel163复测完成，实体反馈待补。已部署内核163')
s = re.sub(r'^\| 原生显示 \|.*$', '| 原生显示 | 165组合kernel163+boot164：固件复位回调Success、native CTRL先停再清CTL、TX后亮屏；Phosh21.45秒，24次DPMS/12门控及601秒同boot/PID通过，关键错误0 | 实体edk2→Linux白屏/花屏效果待用户回来观察；164首启音频WARN未在165重现、原因未知；157重启原因未知，休眠/更长期稳定性开放 |', s, flags=re.M)
p.write_text(s)
print(json.dumps(summary), flush=True)
