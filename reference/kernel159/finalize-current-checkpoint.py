from pathlib import Path
import hashlib,json,re
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel159';out=Path('/mnt/e/edk2-samurai-out/kernel159')
steady=json.loads((out/'steady-validation.json').read_text())
assert steady['same_boot'] and steady['critical_counts_zero'] and steady['pids_preserved'] and steady['error'] is None and steady['sample_count']==21
(ref/'steady-validation.json').write_bytes((out/'steady-validation.json').read_bytes())
proofs={}
for n in ['first-evidence-private.tar.gz','steady-private.tar.gz','preflash-private.tar.gz','quiesce-private.tar']:
    p=out/n;proofs[n]=dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(ref/'evidence-archives.json').write_text(json.dumps(proofs,indent=2)+'\n')
summary=dict(stage=159,actual_kernel_build=158,two_new_boots_accepted_by_kernel_checks=True,
    total_standard_dpms_transitions=48,actual_wake_frame_gate_count=24,all_tx_wait_then_backlight=True,
    phosh_start_uptimes=[19.99,19.56],previous_phosh_start_uptime=79.67,
    latest_continuous_observation_seconds=steady['elapsed_seconds'],current_boot_observed_until_uptime=steady['last_sample_uptime'],
    same_boot_and_desktop_pids_preserved=True,full_boot_kms_dsi_dpu_gpu_warning_counts_zero=True,
    no_ufs_uic_timeout_seen_in_current_boot=True,temporary_boot_recorder_disabled=True,
    user_confirmed_manual_wake_no_flicker=True,physical_boot_transition_feedback_pending=True,
    previous157_uncommanded_reboot_cause_unknown=True,goal_complete=False)
(ref/'current-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
p=root/'NEXT-SESSION.md';s=p.read_text()
s=s.replace('阶段158首次启动通过，159准备同镜像重启复测','阶段159第二次158启动和稳态观察通过，实体开机过渡反馈待补')
start=s.index('首次158的现场记录从SSH就绪后');end=s.index('\n\n## 显示修复链',start)
s=s[:start]+'''首次158的现场记录从SSH就绪后230.65秒开始；92.94秒无丢失，快照是晚期live，不能声称为首帧快照。159保持同一158镜像重启，没有刷写；新boot已确认，CTRL/CTL接管和全boot零关键错误通过。早期服务17.72秒记录、93.05秒无丢失，初始TX等待位于真实PP TX done后44微秒。Phosh19.56秒，两次累计48次DPMS、24次亮屏门控通过。

159连续601.09秒/21次采样到uptime1006.20秒，同一boot、桌面PID保持，KMS/DSI/DPU/GPU/WARN/UFS UIC timeout0、taint0。临时159启动服务已停止并退出boot runlevel。当前源/镜像/实机均158，当前boot身份在kernel159私人first-boot收尾目录，旧preflash/source身份不能再用于切换。用户确认手动开关屏无闪屏，开机白屏/花屏过渡问题的实体反馈仍待补，goal active。[159验收](reference/kernel159/README.md)
'''+s[end:]
p.write_text(s)
(root/'NEXT-SESSION-PROMPT.md').write_text('''继续Realme X2 Pro显示修复收尾，先读NEXT-SESSION.md、reference/kernel158/README.md、reference/kernel159/README.md、WORKING-BOUNDARIES.md。当前实机/源码/Image均158，boot132/modules132/software132+Mesa149保持。158在DPU CTL清理前停止固件DSI，再native PHY初始化，并在首帧TX完成后亮屏。两次真实新启动全boot KMS/DSI/DPU/GPU/WARN0，Phosh19.99/19.56秒（旧79.67秒），累计48次标准DPMS、24次实际首帧门控顺序通过；分区/NV/模块/Mesa核验通过。159早期记录17.72秒起、93.05秒无丢失，初始TXwait在PPdone后44微秒；连续601.09秒到uptime1006.20同boot/PID稳定，UFS UIC timeout0，临时boot记录器已禁用。

用户已确认手动几次开关屏无闪屏；实体开机“命令行→锁屏”白屏/花屏过渡的异步问题仍待回答。先处理此反馈，不再因旧身份重放159 F1，也不用旧preflash身份切换；当前boot私人收尾在kernel159 first-boot目录。157曾首启CTL失败、一次重探测恢复后未经指令重启，用户确认无操作，原因未知；下一RAM boot UFS阻塞、无磁盘FS，已保存w并一次b完成受理F1后只刷158。该历史仍保留，不能宣称根因已证明。goal active，未把物理启动验收替换成日志通过。合并公开补丁reference/kernel158/display-fix-from154.patch已逆向apply检查，基于154含14文件修改。其余硬件开放项保持。
''')
p=root/'DOCS-INDEX.md';s=p.read_text();start=s.index('当前进展与交接：');end=s.index('\n\n',start)
s=s[:start]+'''当前进展与交接：[158修复与合并补丁](reference/kernel158/README.md)、[159复测](reference/kernel159/README.md)、[当前检查点](NEXT-SESSION.md)、[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。当前内核158，两次新启动关键错误0，Phosh约20秒，48次DPMS和24次首帧门控通过；用户确认唤醒无闪屏，601秒持续观察同boot/PID稳定。实体开机白屏过渡反馈待补，157未指令重启原因未知继续留档。'''+s[end:];p.write_text(s)
p=root/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text().replace('阶段158首次启动、159复测准备','阶段159第二次158启动及稳态观察完成')
s=re.sub(r'^\| 原生显示 \|.*$', '| 原生显示 | 158两次CTRL先停机再清CTL、自动桌面、全boot关键错误0；用户确认唤醒无闪屏；48次DPMS与24次首帧门控、601秒同boot/PID稳态通过，Phosh约20秒 | 实体开机白屏/花屏过渡反馈待补；157未指令重启原因未知，系统休眠与更长期稳定性开放 |',s,flags=re.M);p.write_text(s)
print(json.dumps(summary),flush=True)
