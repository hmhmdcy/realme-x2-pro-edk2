from pathlib import Path
import hashlib,json,re,tarfile
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel158';out=Path('/mnt/e/edk2-samurai-out/kernel158')
for name in ['runtime-validation.json','cycles-validation.json','boot-timing-validation.json','live-observation-validation.json']:
    (ref/name).write_bytes((out/name).read_bytes())
(root/'reference/kernel157/desktop-recovery-validation.json').write_bytes((out/'prior-desktop-recovery-validation.json').read_bytes())
(root/'reference/kernel157/connection-loss-validation.json').write_bytes((out.parent/'kernel157/connection-loss-validation.json').read_bytes())
r=json.loads((ref/'postboot-tools-validation.json').read_text());r['archive_sha256']=hashlib.sha256((out/'postboot-tools-private.tar').read_bytes()).hexdigest();r['late_live_snapshots_not_initial_snapshots']=True
(ref/'postboot-tools-validation.json').write_text(json.dumps(r,indent=2)+'\n')
with tarfile.open(out/'first-evidence-private.tar.gz') as t:
    d=t.extractfile('k158-first-runtime/dmesg-private.txt').read().decode()
    stop=d.index('DSI firmware stop before PHY: CTRL=0x1f5 -> 0x0');ctl=d.index('boot CTL0:');clear=d.index('boot CTL0 cleared:')
    assert stop<ctl<clear
    assert d.count('DSI firmware stop before PHY:')==1
    order=dict(stage=158,actual_kernel_build=158,inherited_enabled_controller_stopped=True,
        stop_before_first_ctl_cleanup=True,ctl_cleanup_success=True,one_shot_stop_count=1,
        full_boot_kms_dsi_dpu_gpu_warning_counts_zero=True,physical_wake_user_confirmed=True,
        physical_startup_transition_pending=True,unexpected157_reboot_user_reports_no_operation=True,
        same_image_second_boot_pending=True,goal_complete=False,
        first_evidence_archive_sha256=hashlib.sha256((out/'first-evidence-private.tar.gz').read_bytes()).hexdigest())
    (ref/'first-boot-validation.json').write_text(json.dumps(order,indent=2)+'\n')
text='''# Realme X2 Pro 当前检查点

2026-10-13，阶段158首次启动通过，159准备同镜像重启复测。当前规则只以 [WORKING-BOUNDARIES](WORKING-BOUNDARIES.md) 为准。

## 当前实际状态

现机 #158，boot132/logdump158/modules132/software132 加 Mesa149 修复。源码、Image、已部署 logdump 同为158；WSL源码 `/home/cy122/pmos-samurai-kernel136/kernel`。实际release仍为 `7.3.0-rc6-rmx1931-samurai-k132+`，须按 uname -v 核对构建号，DRM card 按 by-path 解析。

158首次日志确认 DSI CTRL=0x1f5 先停至0，然后 CTL0 清理完成，随后 native PHY/DSI初始化。自动Phoc/Phosh启动，Phosh uptime19.99秒，此前155为79.67秒。全boot KMS初始化失败、DPU timeout、DSI error、GPU fault、WARN均0，taint0；音频DMA prepare9是既有待办。用户已手动多次开关屏并确认无闪屏，自动24次标准DPMS无新增错误。logdump读回及boot/persist/模块/NV/Mesa核验通过。[158证据](reference/kernel158/README.md)

首次158的现场记录从SSH就绪后230.65秒开始；92.94秒无丢失，快照是晚期live，不能声称为首帧快照。早期时序来自完整dmesg及bootconfig trace。159将保留同一158镜像，不刷写，安装早期启动记录服务，再完成新启动及实体命令行到锁屏过渡验收。当前源158身份在kernel159私人准备目录；新boot未确认之前不复用旧身份执行切换。

## 显示修复链与既有失败

153 probe GPIO GPIOD_ASIS、prepare才初始化方向，避免先破坏固件显示；154在native power_on停止CTRL后重写时序，仍有首次白屏和DSI欠载。155同154重启无DSI错误，但用户偶发唤醒闪屏及启动慢。

156实现原厂首帧背光策略；DPU等待TX完成，12次实机亮屏门控顺序通过，24次DPMS通过，但首次78条DSI错误。greetd设置rc_before=samurai-radio，保留无线45秒等待与NV流程，Phosh由79.67秒提前至20.62秒。

157把停机提前至PHY配置前；首次CTL -22发生更早，停机路径未执行。一次panel重探测与原initial_session恢复Phoc/Phosh后发生新boot；用户确认没有拔插/重启等操作，原因未知、pstore为空。新157 RAM boot UFS探测阻塞，没有挂载磁盘文件系统。158根据当前RAM身份一次F1受理，device_shutdown被存储探测阻塞；保存SysRq w，再次证明同一RAM-only后一次SysRq b完成挂起bootloader切换，只刷logdump158。[157记录](reference/kernel157/README.md)

158进一步在SM8150 DPU清理boot CTL前停止全部已绑定DSI，复用一次性PM/读回保护；156首帧函数和157before-PHY幂等回退保持。22项真实函数普通与ASAN/UBSAN、完整构建/W=1/checkpatch/FAT通过。770模块中两个仅GNU build-ID不同，其余全部字节一致，原模块132兼容复用。[158补丁](reference/kernel158/before-ctl-stop.patch)

152 worker同步候选仍拒收，不混入后续候选。当前电源测试使用DisplayConfig.PowerSaveMode，wlr-randr --off曾移除唯一输出导致Phosh崩溃。实体开机过渡、跨boot与更长稳定性待验收，goal保持active。

## 其它待办

GPU147/149既有修复保持，150无Mesa本地补丁降级未部署；软件包/完整rootfs需携带Mesa0015补丁。151软件数据库差异、充电保护、音频首次DMA/停止链、camera、传感器、蜂窝/GNSS/指纹/NFC、休眠与长稳保持开放。[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。
'''
(root/'NEXT-SESSION.md').write_text(text)
(root/'NEXT-SESSION-PROMPT.md').write_text('''继续Realme X2 Pro显示修复，先读NEXT-SESSION.md、reference/kernel158/README.md、reference/kernel157/README.md和WORKING-BOUNDARIES.md。现机、源码、Image为158，boot132/modules132/software132+Mesa149保持。158先停止固件DSI CTRL1f5至0，再清理CTL并初始化PHY；首次自动桌面成功，全boot KMS/DSI/DPU/GPU/WARN0，taint0，音频DMA9。用户已确认多次开关屏无闪屏，自动24次DPMS、分区/模块/NV/Mesa核验通过，Phosh由79.67秒提前至19.99秒。

159准备同一158镜像重启，不刷写；当前身份/停机证据在kernel159私人目录。先核实实际切换阶段，不能重放已受理F1。159服务将从早期记录新boot，验证首帧门控、实体启动白屏过渡及跨启动稳定。158初次采集从230.65秒开始，快照是late live，别当首帧；157出现CTL失败、一次重探测恢复后未指令重启进入UFS阻塞RAM，用户确认未操作，原因未知。158从该RAM的新身份、无磁盘FS证明出发，一次F1受理但shutdown阻塞，保存w后一次b完成挂起切换，只刷logdump158。当前goal active，不凭日志零错误替代实体验收。
''')
p=root/'DOCS-INDEX.md';s=p.read_text();start=s.index('当前进展与交接：');end=s.index('\n\n',start)
s=s[:start]+'''当前进展与交接：[158证据](reference/kernel158/README.md)、[156会话](sessions/156-first-frame-backlight-and-early-desktop.md)、[检查点](NEXT-SESSION.md)和[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。现机158/software132加Mesa149；首次CTRL停机早于CTL清理、自动桌面与零错误通过，Phosh19.99秒，用户确认唤醒无闪屏。159准备同镜像重启，实体启动过渡与稳定性待验收。157未指令重启及UFS RAM阻塞仍保留，GPU147/149结论保持。'''+s[end:];p.write_text(s)
p=root/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text();s=s.replace('阶段154/155观察。已部署内核154','阶段158首次启动、159复测准备。已部署内核158').replace('../../reference/kernel154/README.md','../../reference/kernel158/README.md',1)
s=re.sub(r'^\| 原生显示 \|.*$', '| 原生显示 | 158首次CTRL停机早于CTL清理、自动桌面和全boot KMS/DSI/DPU/GPU/WARN0；用户确认开关屏无闪屏，24次DPMS通过，Phosh19.99秒 | 159同镜像跨boot、实体命令行到锁屏过渡与长稳待验收；157未指令重启/UFS RAM阻塞原因未知，休眠仍开放 |',s,flags=re.M);p.write_text(s)
print(json.dumps(order),flush=True)
