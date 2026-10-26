from pathlib import Path
import json
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel118'
build=json.loads((ref/'kernel-build-validation.json').read_text())
health=json.loads((ref/'current115-health-validation.json').read_text())
package=json.loads((ref/'candidate-package-validation.json').read_text())
assert build['embedded_cpio_semantically_identical'] and package['fat_check_pass']
assert health['observation_seconds']==300 and health['window_dpu_timeouts']==health['window_gpu_faults']==0
summary='阶段118完成隔离#118显示复位最终读修正、实际C函数五场景测试、完整Image/modules/DTB构建和logdump FAT回读；尚未部署。DTB与115字节相同，14,803个内建导出相同，764个模块去debug/build-id后字节相同；CONFIG_MODVERSIONS关闭，不把0 CRC当版本校验。当前手机仍原#115启动，DRM/Phosh/Phoc保持、taint0，新增300秒/10采样窗口无DPU/GPU新增故障，累计DPU1；PCM closed/功放静音、SLPI供电0、trace off、NV6/source4/vendor保持。永久启动/长稳仍未验收。'
session='sessions/118-final-reset-read-build-and-host-space-recovery.md'
text=f'''# 阶段118：复位最终读候选与主机构建空间恢复

2026-10-12。完整系统goal active；无人值守继续，不要求人工检查。

{summary}

## 最小显示修正及验证

来自阶段117的实际源码证据：2ms轮询读取SW_RESET后睡眠，再检查期限，可能返回睡眠前旧位。[Linux上游iopoll.h](https://raw.githubusercontent.com/torvalds/linux/master/include/linux/iopoll.h)同样要求超时后仍操作一次。隔离115基础只修改dpu_hw_ctl_poll_reset_status的最终返回，重新读真实bit0；2ms期限、20–50us睡眠、bit持续置位时错误、全部IOMMU前quiescence/INTF stalled mask检查保留。未合入116 CAMSS/media配置，不混入板级摄像头修改。

直接提取115和118的实际C函数，用确定性MMIO/时间stub编译执行：旧函数在2500us延迟唤醒且1000us时硬件已clear的场景误报；新函数复读通过。already idle、普通多轮完成、普通持续置位/有界期限及延迟持续置位均通过。只是证明该源码问题，不证明它解释真机全部RCU/CTL回归。

完整Image/modules/DTB构建通过。第一次olddefconfig因额外Rust PATH探测出编译器metadata，已撤除额外PATH并重新完整构建，使配置除initramfs绝对路径外与115一致。tracked源码只有一个DPU文件不同；全树diff-check命中115已有EUD earlycon两处尾随空白，保留基线，只对本次修改文件做check通过。

115的Module.symvers后来仅包含14803个vmlinux导出，118完整构建含16415条，不能直接称两份完整表相等；逐一核对14803个内建导出相同，并对764个旧/新.ko去debug及build-id后逐字节相同，sample vermagic一致。CONFIG_MODVERSIONS关闭，所有0 CRC不是独立ABI证明。initramfs源及CPIO成员内容/权限/uid/gid/设备号语义相同；CPIO原始hash因构建metadata变化不同。IPA TX delay修正保留，115/116 Image基线hash未变。

118 Image SHA256 {build['artifact_sha256']['arch/arm64/boot/Image']}；DTB f3e970e5967c4f6768b3b8e2b54dad833a7a7f532eb6ae856093c3c1514877da，与当前115相同。私有logdump-k118-ctl-final-read.img大小67108864，SHA256 {package['logdump_sha256']}，仅替换FAT中的Image，samurai.dtb保持；FAT成员只有Image/DTB，读取字节相等、fsck.fat -n通过。UEFI仍复用已验证115 boot/嵌入DTB。部署候选只需logdump，当前尚未做新的preflash守卫、排空、freeze或刷机。

## 主机空间故障与隔离恢复

第一次普通clone在C盘host剩余0时出现I/O error、WSL ext4转只读，WSL报告DISK_CORRUPTED。立即停止候选，不部署。对九个本任务对应RMX1931/Samurai recovery IMG启用可逆NTFS压缩，内容hash前后一致，原位置保持；随后WSL正常启动、journal recovery complete/rw。没有运行在线fsck或强制remount，不宣称完整主机fsck。

只删除本轮新建且未完成的118 clone，没有删除115/116或其它任务。fstrim后C剩余约2.4GiB，旧115/116 Image hash复核通过。后续候选在E盘新建私有20GiB ext4文件，挂载到/home/cy122/pmos-samurai-kernel118；clone/build都写E，C没有继续承载大副本。不是手机分区格式化，也不迁移原WSL VHD。WSL闲置会卸载loop，ensure-build-volume.py在下一操作中按文件大小、label、loop backing path核对后重新挂载；不能把未挂载的空目录当源码损坏，也不能向该目录直接clone。

## 现机五分钟健康窗口

仍阶段117恢复后的原115第三次启动。10次间隔30秒采样，实际跨度至少300秒：Phosh/Phoc与DRM保持，taint0，窗口DPU0/GPU0、累计DPU1。PCM closed双功放powered0/muted1，SLPI offline/vdd/vddio0，traces0/0，Wi-Fi up/zram。NV6/source4/vendor全部OK。归档全成员hash和同boot身份核对通过，SHA256 {health['archive_sha256']}。仅idle窗口，没有屏幕/触摸/听音/应用压力或休眠验收。

首版收尾用了错误sensor-power debugfs路径，300秒采样已经完成但metadata命令失败；最终用真实/sys/devices/platform/sensor-power/state补齐并重新核验。同样修正busybox date默认文字格式与ISO格式的采样解析，不删除失败证据。没有重启、flash、用户登录配置变更、GUI输入或声音播放。

## 下一飞轮

先完成当前115新preflash：fresh boot/logdump/persist/GPT18/NV6/source4/vendor/用户音频及GUI状态，私有备份与当前套件匹配。沿当前已恢复GUI状态排空greetd/用户会话、音频功放/ADSP、Wi-Fi/蓝牙/ModemManager/MPSS，sync和本boot fsfreeze成功才允许EUD F1；不能套无GUI旧脚本或旧第二启动守卫。只刷118 logdump，115 boot不变；记录启动RCU/CTL/DRM/Phosh、恢复前后所有状态，有界失败则留档并回退当前115套件或转项。

rootfs115 fixed 936包/764模块完整镜像保持，未全量刷userdata。摄像头116候选未部署，BIN parser stall已转项；C-PHY/CCI/CAMCC/DMA/ICC/QoS、完整传感器、GNSS fix、蜂窝数据/通话、指纹、充电、休眠/长稳仍开放。所有身份/固件/BIN/日志/镜像私有，无GPT/NV/persist写入、erase、对外消息/呼叫或文档push。goal不complete。
'''
(root/session).write_text(text)
for name in ['README.md','FLYWHEEL.md']:
    p=root/name;t=p.read_text();marker='[阶段117](sessions/117-parser-boundaries-and-same-boot-desktop-recovery.md)'
    t=t.replace(marker,f'[阶段118]({session})，'+marker,1)
    old=t.split('\n\n')[2]
    assert old.startswith('阶段117')
    p.write_text(t.replace(old,summary,1))
p=root/'NEXT-SESSION.md';t=p.read_text().replace('阶段117（2026-10-12）','阶段118（2026-10-12）',1)
t=t.replace('先读[阶段117]',f'先读[阶段118]({session})、[阶段117]',1)
anchor='当前手机仍第三次#115启动'
idx=t.index(anchor);t=t[:idx]+summary+'\n\n'+t[idx:]
t+='\n阶段118下一步以上文session为准：118在E盘私有20GiB ext4 loop内，先ensure挂载；已完成最小CTL最终读修正/五场景/完整构建/764模块字节比较/FAT打包，未部署。只需logdump但必须先fresh preflash和本boot已恢复GUI完整排空/freeze/F1。C约2.4GiB，禁止再复制完整kernel到C或扩大WSL VHD。\n'
p.write_text(t)
p=root/'DOCS-INDEX.md';t=p.read_text().replace('当前：[阶段117]',f'当前：[阶段118]({session})、[阶段117]',1)
t=t.replace('| sessions/117-',f'| {session}、reference/kernel118/ | 显示最终读最小候选/实际C测试、E盘隔离构建、764模块/FAT校验与现机300秒健康；未部署 |\n| sessions/117-',1);p.write_text(t)
p=root/'linux-port/docs/HARDWARE-STATUS.md';t=p.read_text().replace('，阶段117）','，阶段118）',1)
t=t.replace('[阶段117]',f'[阶段118](../../{session})、[阶段117]',1)
t=t.replace(t.split('\n\n')[3],summary,1)
t=t.replace('随后45秒0新增','随后45秒及300秒窗口0新增').replace('修复命令帧/CTL reset接管，保留IOMMU前quiescence；','118最小最终读候选构建/FAT验证通过未部署，保留IOMMU前quiescence；')
p.write_text(t)
print('CHECKPOINT118_UNDEPLOYED_CANDIDATE_AND_VERIFIED_CURRENT115_DOCUMENTED')
