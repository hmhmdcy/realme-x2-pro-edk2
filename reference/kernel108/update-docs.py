#!/usr/bin/env python3
from pathlib import Path
import json
import re

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel108'
out = Path('/mnt/e/edk2-samurai-out/kernel108')
names = ['README.md', 'FLYWHEEL.md', 'linux-port/README.md', 'linux-port/docs/HARDWARE-STATUS.md',
         'NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md', 'HANDOVER-NEXT.md', 'DOCS-INDEX.md']
before = {name: (root / name).read_text() for name in names}
backup = out / 'public-docs-before.json'
assert not backup.exists()
backup.write_text(json.dumps(before, ensure_ascii=False, indent=2)+'\n')
summary = json.loads((ref / 'checkpoint-validation.json').read_text())
session = '108-display-flicker-and-panel-state-handover.md'
short_status = '''手机仍为Linux #106（阶段107镜像）；阶段108只做诊断、一次正常DRM开关屏和一次同镜像暖重启，没有构建新内核或刷分区，实际内核源码/config/DTB/CPIO/boot/logdump保持。
用户确认白底不规律滚动花屏；故障现场持续DSI status=c（FIFO/MDP FIFO下溢）、显示完成超时累计2。单次DRM开关屏虽然ioctl返回0，但用户确认黑屏；日志有DCS关屏/睡眠-110及already prepared/enabled。面板驱动断电后返回传输错误，使DRM core保留状态并跳过重新开启，状态处理缺陷已定位、尚未修复；不能把这次开关屏记为通过。
同镜像重启后用户确认黑底Linux命令行可见；405.44秒检查点DSI错误0、显示超时0、双DSP running、taint0。只证明本次命令行恢复，未复查纯白光学画面，未证明首次接管/长稳或永久修复。
新boot自动radio初始化auto0、三个modem服务公告result0、真实PD/固件/RAM COW请求和trace无丢失通过，无手动MPSS恢复。5GHz关联未在60秒窗口完成，后来COMPLETED/5180；最终DHCP和DNS有结果，但网关0/3、HTTP20秒终止且无正文，当前数据复测失败。107的5GHz全流程成功仍是历史证据；2.4GHz577B内容到达但wget收尾超时也保留，本轮未重测2.4GHz。
下一轮使用kernel109新前缀/新bootID/新完整备份，优先修SOFEF03F超时断电后的状态生命周期，再查DSI下溢及5GHz新启动数据失败；不盲目重复开关屏。蓝牙停止不配对，振动按用户要求只看日志/代码，NFC仅控制器，充电收尾保持；Android/data/GPT/NV/persist/SSH/rootfs01/F2FS与旧显示85–88快照保留，私人凭据/身份/固件/原日志/镜像不公开，不提交推送；全硬件goal active。
'''
for name in ['README.md', 'FLYWHEEL.md', 'linux-port/README.md', 'linux-port/docs/HARDWARE-STATUS.md']:
    text = before[name]
    text, count = re.subn(r'手机已部署Linux #106（阶段107）.*?全硬件goal active。\n', short_status, text, count=1, flags=re.S)
    assert count == 1, name
    prefix = '../sessions/' if name == 'linux-port/README.md' else 'sessions/'
    text = text.replace('[session107](' + prefix + '107-qrtr-hello-reply-and-automatic-wifi-start.md)', '[session108](' + prefix + session + ')', 1)
    if name.endswith('HARDWARE-STATUS.md'):
        text = text.replace('session107）', 'session108）', 1)
        replacements = {
            '原生显示面板': ('白底滚动花屏伴DSI status=c；DRM开关屏导致黑屏，状态缺陷已定位；重启恢复黑底命令行，当前DSI/超时0', '修SOFEF03F错误关屏/断电状态，定位下溢；纯白光学、首次启动、休眠和长稳待验收，保留旧快照'),
            'Wi-Fi': ('#106第二次新boot自动radio auto0、公告/PD通过；5GHz最终COMPLETED/5180，但60秒关联窗口及最终网关/HTTP复测失败；107历史5G全流程成功保留', '优先查5GHz新启动数据失败；2.4GHz HTTP收尾及历史reason7/删除等待仍待修，冷启动/休眠/长稳待验收'),
            '蜂窝网络/数据': ('#106两次新boot自动MPSS初始化通过；108检查点连续running约356.36秒，真实固件/RAM COW与PD请求，无fatal/手动恢复', '通话/移动数据未验收；NV不写，冷启动/休眠/长期稳定继续'),
            '音频': ('107原生声卡/双MAX98937/WCD934x与API7/API2、有限播放/DMIC0非零回归历史保留；本轮无播放/录音，PCM关闭、功放start0/stop0/failed0', '实际声音/拾音质量/启动瞬态/耳机/DSM/校准/休眠未验收'),
            '蓝牙': ('历史附近扫描通过；本轮停止、HCI为空、模块卸载，无配对连接测试', '用户暂缓配对连接；保留UART power-on phase2错误历史待办'),
        }
        for label, cells in replacements.items():
            text, count = re.subn(r'^\| '+re.escape(label)+r' \|.*$', '| '+label+' | '+cells[0]+' | '+cells[1]+' |', text, count=1, flags=re.M)
            assert count == 1, label
        text = re.sub(r'下一项优先重复启动、2\.4GHz数据/HTTP收尾与其它硬件；.*?NFC只控制器。', '下一项优先显示错误关屏状态/DSI下溢及5GHz新启动数据失败，其后2.4GHz HTTP收尾和其它硬件；振动机械确认暂缓，BT不配对连接，NFC仅控制器。冷启动/休眠/长期稳定仍未验收。', text, count=1, flags=re.S)
    (root / name).write_text(text)

detail = f'''# 阶段108：显示滚动花屏、错误关屏黑屏与交接（2026-10-11）

手机仍Linux #106，镜像部署记录见[107](107-qrtr-hello-reply-and-automatic-wifi-start.md)。本轮未改实际内核源码或config/DTB/CPIO，未构建Image，未刷任何分区。用户要求更新文档并准备下一会话；状态缺陷只定位，尚未实现补丁。

用户依次报告“白底上有滚动条纹”“白色背景，不规律滚动闪烁的花屏”。这不是仅凭肉眼就能认定的屏幕硬件损坏。先保存SSH dmesg、DRM/encoder、亮度、display trace/snapshot，再尝试一次正常DRM关屏/开屏，随后保存黑屏现场并受控暖重启。

## 显示发现与失败证据

- 故障现场原生1080×2400@60、command mode、brightness/actual_brightness均400/max2047。actual_brightness在这个驱动没有硬件读回实现，不能把sysfs数值当作光学亮度验证。
- 日志环中持续`dsi_err_worker: status=c`，受限速/环滚动影响不是整个启动错误总数。实际源码中FIFO=0x4、MDP FIFO underflow=0x8；worker在该位出现时调用dsi_sw_reset。DPU underrun计数仍0，不等于DSI FIFO没有下溢；故障前frame_done_cnt为2，这个名称实际统计完成超时。
- 一次正常DRM_SETCRTC关闭/恢复原fb93，ioctl退出0；用户确认**黑屏**，因此功能测试失败。保留旧display snapshot摘要一致，未清空或重武装旧故障快照。
- 随后日志：backlight disable -110、SET_DISPLAY_OFF -110、ENTER_SLEEP_MODE -110，以及“Skipping prepare of already prepared panel”“Skipping enable of already enabled panel”。黑屏时bl_power=4，亮度软件值仍400。
- 源码链条：`sofef03f_unprepare()`发送睡眠命令，随后无条件`sofef03f_power_off()`，却返回累积的DCS错误；`drm_panel_unprepare()`遇负返回值不清prepared。disable的负返回值同样阻止core清enabled。下一次prepare/enable因此被跳过，硬件断电与软件标志矛盾。这解释了本次错误关屏后黑屏；还没有证明最初DSI下溢的触发原因。
- 不把删除错误日志、延长等待、增加自动开关屏当修复。下一轮应审查超时后的关屏/断电完成语义、regulator引用平衡和重新prepare/enable路径，保留错误可见；先做真实函数的失败路径验证，再新守卫构建/刷入。

保存全部现场后，经WPA→BT→ath10k→MPSS受控停止、真实F1回执、独立fastboot身份/product校验，只执行同镜像reboot。用户确认**黑底Linux命令行可见**。新boot面板44.248578秒报告power mode0x9c；405.44秒检查点DSI错误0、显示超时0、bl_power0、brightness400、taint0。纯白画面未再做光学确认，本次成功不能覆盖旧失败或宣称永久修复。

## 无线现状与新失败

第二个新boot仍自动radio初始化成功：boot-finished0，modem首次up49.082914秒，检查点连续running356.357086秒；三个modem服务公告发送result0，真实kernel/elf_loader PD回复及固件/RAM COW NV请求，无trace丢失、无手动MPSS恢复/ADSP重启。107的QRTR修复在重复暖重启得到支持，未做断电冷启动或休眠。

5GHz私人配置重新放入RAM后，60秒窗口结束时仍SCANNING，保留`ASSOCIATION_NOT_COMPLETED_WITHIN_60_SECONDS`失败原件。之后自行到COMPLETED/5180。对已有连接做一次有限复测：DHCP得到租约、DNS有答案，但网关ping0/3、HTTP20秒被终止、正文0字节，result为`FINAL_NETWORK_TEST_FAILED`。**当前连接状态不等于网络流量正常**；本轮不能重新宣称5GHz全流程通过。107的5GHz成功记录仍有效，不能用新失败修改它。

2.4GHz本轮没有重测。107的2462MHz认证/DHCP/网关/DNS及577字节内容到达、wget收尾超时仍保留；历史reason7/密钥删除等待另行保留。本轮已经自写并Werror构建被动HTTP TCP80 AF_PACKET捕获工具（仅allowlist、最长60秒、上限8MiB），尚未部署/抓包。下一轮分别定位5GHz新失败与2.4GHz收尾，避免混为密码错误。

## 保存与验收边界

完整boot96MiB和logdump64MiB重新从80个2MiB块收取并逐块校验、重组和比对；一次SCP reset的部分块保留`.partial-first`，终止后只恢复未完成块。完整两分区、NV六项、persist与stockDTBO不变；实际内核源码diff、untracked、initramfs文件、config/DTB/CPIO/Image均与108开始时一致。rootfs01/F2FS候选未刷，原段落保留。

检查点SHA256 `{summary['checkpoint_sha256']}`，31个直接文件、3个内嵌原包，合计74项SHA验证；其余故障/重启前原包保留在私人kernel108，摘要见[manifest](../reference/kernel108/private-archive-manifest.json)与[核验](../reference/kernel108/checkpoint-validation.json)。原日志、身份、凭据、固件、NV响应、镜像和二进制均只在本机私人目录。早期重启后第一次encoder读取因debugfs未挂载而为空，随后挂载后重新取证，不把空读数当健康状态。

本轮无蓝牙配对/连接、振动脉冲、音频播放/录音或充电探针。107音频/DMIC与历史蓝牙扫描/振动电气结果单独保留，不继承为本轮验收。全15组目标仍active；没有提交、推送或运行文档同步发布脚本。

研究参考：[DSI上游源码](https://kernel.googlesource.com/pub/scm/linux/kernel/git/next/linux-next/+/8e67585674c6cf2330d411eed8031423d4689c2b/drivers/gpu/drm/msm/dsi/dsi_host.c)支持FIFO错误与reset路径的核对；[SM8150 hotdog实测报告](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-17-dsi-dsc-transport-errors.md)记录另一面板的DSC花屏与软复位失败，仅作为仪器/恢复边界参考，不能把它的status5、slice几何或结论移植为本机根因；[旧MDP5讨论](https://lists.openwall.net/linux-kernel/2019/11/11/591)同样只作线索。

继续工作见[NEXT-SESSION](../NEXT-SESSION.md)和[短提示词](../NEXT-SESSION-PROMPT.md)。下一轮kernel109，严禁原样重放108旧bootID/PID/guard目录；DTB改变必须真重建EDK2嵌入DTB。
'''
assert not (root / 'sessions' / session).exists()
(root / 'sessions' / session).write_text(detail)
next_text = f'''# 下一会话：显示状态修复与Wi-Fi新启动数据回归

先读[阶段108](sessions/{session})、[15组状态](linux-port/docs/HARDWARE-STATUS.md)及[核验](reference/kernel108/checkpoint-validation.json)。全硬件goal active，无预算；用户本轮要求保存文档和短提示词，未创建新会话、未构建或刷入面板修复。

{short_status}
当前身份用私人`E:/edk2-samurai-out/kernel108/runtime-boot-id-after-private.txt`核对，实际仍#106（13:48:23 CST构建），不能再用kernel107的旧bootID。检查点405.44秒，SHA `{summary['checkpoint_sha256']}`，31直接文件/3内嵌包/74项验证；后续只读确认仍COMPLETED/5180。进入下一轮先重新获取当前现场和身份，用kernel109全新前缀，不能重放旧目录。

1. 优先修`drivers/gpu/drm/panel/panel-samsung-sofef03f.c`失败关屏路径：DCS -110后已经physical power-off，但返回错误使`drm_panel_unprepare/disable`保留prepared/enabled，重新开启被跳过。审查disable→unprepare和enable→backlight全链；确保强制关屏、regulator引用平衡、原厂等待/电压/引脚和错误日志保持。源码还没改，勿把计划写成已部署。拿实际函数做错误路径验证，再按新守卫构建刷入，单次有界复测。
2. 原滚动花屏与DSI status=c/FIFO+MDP FIFO下溢同时出现，worker反复reset；DPU underrun0不能排除它。旧启动已保存故障kms/clk/trace/snapshot和用户黑屏观察；当前新boot零错误不算永久修复。保留85–88及108原件，检查首次接管/TE/autorefresh、DSI控制/7nm PHY/DSC，勿盲加MDSS复位、改寄存器或重复开关屏。
3. 当前5GHzCOMPLETED/5180，60秒关联窗口失败，随后DHCP和DNS有结果、网关0/3、HTTP20秒/0字节失败。没有后续成功流量测试，勿称当前Wi-Fi正常。107全流程通过是历史证据。下一步有限捕获wlan0 TCP/ARP/ICMP路径或正确限定测试端点；108 HTTP工具只构建未部署，需新输出/真实程序PID和allowlist。2.4GHz107收到577B但wget结束超时，历史reason7/删除等待独立保留；本轮没有重测2.4。
4. 两轮#106新boot自动MPSS服务/PD/TFTP/RAM COW启动支持QRTR修复，无手动恢复；冷断电/休眠/长期稳定未验收。保留主动endpoint/MHI resume HELLO与NS先回复后公告；不要全量回退544d85d或改NV假治故障。

实际Linux源码`/home/cy122/x2pro-linux/linux`、initramfs`/home/cy122/x2pro-linux/initramfs`、EDK2`/home/cy122/edk2-samurai/repo`。当前Image/DTB/CPIO摘要见私人108/preparation.json及107/kernel-validation.json。显示/radio bootconfig原106不可变路径保持；linux-port/dts旧镜像不覆盖；DTB变更必须重建EDK2内嵌DTB。kernel109构建前保存完整源码/配置/CPIO/初始化目录及boot/logdump备份并核对PARTNAME/容量/身份，授权分区只有boot/logdump。

MPSS通过`/usr/sbin/samurai-modem-remoteproc`按唯一OF/PAS/固件定位，不固定remoteproc编号。SSH用reference/kernel72/usb-ssh.ps1；私有5G/2G配置在108输出目录，密码不写文档/内核/CPIO。HCI为空、辅助模块卸载；用户蓝牙暂不配对连接。振动仅日志/静态分析、不重新提问或发脉冲；NFC仅控制器。音频107真实播放/DMIC历史保留，本轮PCM关闭、功放start0/stop0/failed0。

保留Android/data/userdata/GPT/NV/persist/SSH/rootfs01/F2FS、历史85–88与108快照。NV仅RAM COW；充电收尾，不执行旧OEM/配置/NV/OTP/unseal/FET/OTG/MCU/GPIO/I2C_FORCE探针。原日志/凭据/身份/固件/音频/镜像私人，不提交推送或运行sync-docs-to-repo.sh。USBipd保持Running，EUD最终detached；hrdevmon警告保留，不forcebind。继续15组硬件，验收需区分源码、构建、部署、数字数据与实物可见结果。
'''
(root / 'NEXT-SESSION.md').write_text(next_text)
(ref / 'next-session.md').write_text(next_text.replace('](sessions/', '](../../sessions/').replace('](linux-port/', '](../../linux-port/').replace('](reference/kernel108/', ']('))
prompt = '''继续 Realme X2 Pro Linux适配。先读 NEXT-SESSION.md、sessions/108-display-flicker-and-panel-state-handover.md 和15组状态。手机仍#106，108未刷机；用户已确认重启后黑底命令行可见。优先修SOFEF03F关屏超时后断电却残留prepared/enabled的状态错误，再查DSI status=c下溢/滚动花屏。当前5GHz虽COMPLETED，但网关0/3、HTTP超时，不能称网络正常；2.4GHz收尾问题保留。用kernel109新身份/守卫/完整备份推进，保留Android/数据/NV/F2FS与旧快照，NV仅RAM COW。BT不配对，振动只日志/静态分析，NFC仅控制器，充电收尾。私有材料不公开，不提交推送。
'''
(root / 'NEXT-SESSION-PROMPT.md').write_text('# 下一会话短提示词\n\n'+prompt)
handover = before['HANDOVER-NEXT.md']
handover = re.sub(r'当前交接见 .*?以下阶段88历史保留。', f'当前交接见[阶段108](sessions/{session})和[NEXT-SESSION](NEXT-SESSION.md)：#106不变；滚动花屏/DSI下溢与错误关屏黑屏已取证，重启恢复黑底命令行，面板状态缺陷未修；新启动5GHz已关联但网关/HTTP失败。以下阶段88历史保留，不能当当前操作清单。', handover, count=1)
(root / 'HANDOVER-NEXT.md').write_text(handover)
index = before['DOCS-INDEX.md']
index = index.replace('当前：[阶段107]', f'当前：[阶段108](sessions/{session})、[阶段107]', 1)
index = index.replace('| sessions/88-wifi', f'| sessions/{session}、reference/kernel108/ | 滚动花屏/DSI下溢、错误关屏黑屏状态链、同镜像重启恢复命令行及5GHz新失败；未改内核/刷机 |\n| sessions/88-wifi', 1)
index = index.replace('session88当前进展/短提示词；#89未部署、EDK2内嵌DTB、MPSS/WLFW验证与保留边界', 'session108当前进展/真正短提示词；显示状态修复、DSI下溢、5GHz数据回归、kernel109新守卫及保留边界')
(root / 'DOCS-INDEX.md').write_text(index)
(ref / 'README.md').write_text(f'''# kernel108：显示故障取证与下一会话交接

关联[session108](../../sessions/{session})和[next-session](next-session.md)。手机仍#106；没有修改实际内核、构建新Image或刷分区。用户已确认重启恢复黑底命令行；白底尚未复查。一次DRM开关屏导致黑屏，错误状态路径只定位未修。当前5GHzCOMPLETED，但数据复测失败。

公开目录只有自写工具/脚本、脱敏核验和文档。完整boot/logdump、所有原日志/tar、凭据/身份/固件响应、可执行工具和备份块只在私人E:/edk2-samurai-out/kernel108。

- collect-display-live.sh、inspect-display.py：只读故障现场，保留display snapshot。
- drm-panel-cycle.c、build-display-probe.sh、recover-display-once.sh：实际单次正常DRM关闭/恢复原fb，**ioctl退出0但用户黑屏，功能失败**；SHA守卫/新目录拒绝重放。
- display-recovery-summary.json是首版有限过滤结果，wifi字段为空源于漏指定wpa-control路径，不能据此判掉线；最终事实用checkpoint-validation.json与本会话用户报告。恢复脚本的同一错误已在封存时纠正，不重新执行。
- reboot-display-same-kernel.ps1、reboot-f1.ps1、read-eud.ps1：受控停radio/F1/独立fastboot只reboot，未flash；新boot身份和所有输出私人。
- test-auto-network.sh、final-network-state.sh：分别保存60秒关联超时原件与已有5G连接的网关/HTTP失败，不覆盖或改判。
- http-packet-capture.c、build-probes.sh：被动限定TCP80抓包工具Werror静态构建完成，尚未部署或抓包；不代表数据诊断完成。
- collect-checkpoint.sh、verify-handover.py、checkpoint-validation.json、private-archive-manifest.json：31直接文件/3原包/74项SHA、源码与完整备份/保留核验。
- prepare-tools.py及其余继承辅助工具：本轮新守卫准备记录；下一轮kernel109，不原样重放108目录/bootID/PID。

两个守卫误用历史build-hashes（其中无probe SHA）及带BOM/多行baseline文件，均在关屏执行前拒绝；改为本轮自写工具及独立LF私有bootID后才执行一次。一次重启后debugfs未挂载的空读数保留并补采。全目标active，充电/BT/振动/NFC约束保持，不提交推送。
''')
print('STAGE108_DOCUMENTS_AND_SHORT_PROMPT_UPDATED')
