from pathlib import Path
import json, re
root=Path('/mnt/e/RealmeX2Pro edk2')
report=json.loads((root/'reference/kernel109/checkpoint-validation.json').read_text())
assert report['archives_verified'] and not report['goal_complete']
intro='''手机已刷入Linux #109，并从userdata上的F2FS启动postmarketOS/Nura edge；Phosh、屏幕键盘、USB NCM密钥SSH、NetworkManager管理的2.4GHz Wi-Fi和NTP已运行。正常重启后文件、桌面和Wi-Fi自动恢复，HTTPS复测通过；最新启动显示完成超时0/GPU故障0/taint0。实体画面与触屏解锁仍等待用户确认，不能以截图替代光学验收。
SOFEF03F在DCS关闭/睡眠错误后完成物理断电并允许DRM清理状态，regulator引用平衡修复已构建部署；实际函数ASan/UBSan错误路径验证和一次实机正常DRM关闭/重开通过。旧滚动花屏/DSI下溢及5GHz问题继续保留；最新5GHz有界认证尝试失败，2.4GHz已通过网关、HTTP、HTTPS和重启后自动连接。
本机UCM已接入桌面扬声器/DMIC0，应用层2秒低音量播放退出0，有限录音4.86秒/233280帧/221056非零/无削波，空闲后PCM关闭、两只功放静音且failed0。实际声音/拾音质量未获物理确认。一次错误的应用自动启动配置触发GPU恢复，已撤回并保留原日志，修正后的新启动未复现；长稳仍未验收。
用户本轮明确授权覆盖userdata，已执行erase与F2FS sparse刷写；其旧Android/data不再保留。只刷userdata/logdump，boot固件及DTB保持；六LUN头尾/GPT、NV、persist一致，原rootfs01离线源和85–108历史证据保留。蓝牙不配对连接、振动不发新脉冲、NFC仅控制器、充电探针收尾；私人凭据/身份/固件/日志/录音/镜像不公开，不提交推送；全硬件goal active。
'''
readme=root/'README.md'
text=readme.read_text()
start=text.index('当前状态：')
end=text.index('Unofficial EDK2/UEFI port',start)
text=text[:start]+'当前状态：[session109](sessions/109-pmos-userdata-phosh-and-desktop-audio.md)，[下一阶段](NEXT-SESSION.md)。\n'+intro+'\n'+text[end:]
readme.write_text(text)
fly=root/'FLYWHEEL.md'
text=fly.read_text()
start=text.index('当前硬件接入：');end=text.index('> 2026-10-08',start)
text=text[:start]+'''当前硬件接入：[session109](sessions/109-pmos-userdata-phosh-and-desktop-audio.md)与[下一阶段](NEXT-SESSION.md)。
'''+intro+'''
持久F2FS系统已上线。日常回归使用reference/kernel109/reboot-pmos-persistent.sh的正常OpenRC重启，先停止桌面/NM/WPA/BT/ath10k/MPSS并核验NV、同步文件，再由PID1关机。重启后用既有com-up恢复EUD通知，等待NCM和SSH服务启动；从请求到可用可能需数分钟。关键日志仍保存于设备并校验SSH导出，EUD仅辅助。
F1仍用于已核验的诊断环境→fastboot刷机路径；持久根仍rw时不直接重放旧F1流程。一次尝试remount-ro被占用拒绝，随后正常OpenRC重启成功。新候选仍须新身份、新现场、完整boot/logdump及GPT审计；现有flash-pmos.ps1会erase userdata，不能拿它作日常重启工具。

'''+text[end:]
fly.write_text(text)
hardware=root/'linux-port/docs/HARDWARE-STATUS.md'
text=hardware.read_text();end=text.index('| 功能组 |')
text='# RMX1931 Linux 硬件接入清单（2026-10-11，session109）\n\n15组用户可使用硬件保持。\n'+intro+'\n'+text[end:]
rows={
'触摸':'S3706A在#109注册为event3；此前真实点按/移动/释放/多点通过 | 本轮Phosh解锁/点按仍待用户确认；方向/边缘/休眠/长稳',
'原生显示面板':'#109面板状态修复已部署，错误路径测试与一次正常DRM周期通过；Phosh截图1080x2400，最新新boot显示超时0 | 实体显示/旧滚动花屏与DSI下溢、纯白光学、首次接管/休眠/长稳',
'GPU':'FD640硬件GLES2渲染Phosh；最新新boot无GPU故障/taint0；历史Turnip像素/fence回读保留 | 错误自动启动配置曾触发GPU恢复并保留；应用压力/休眠/长稳',
'普通USB与OTG':'NCM/密钥SSH/SCP与EUD共存；持久系统重启后恢复，完整boot保持/当前logdump匹配 | OTG/USB3/休眠/重置/长稳',
'Wi-Fi':'NetworkManager 2.4GHz同本机地址、DHCP/HTTP/HTTPS与重启自动连接通过 | 5GHz最新认证有界失败；历史107成功保留；冷启动/休眠/长稳',
'音频':'本机UCM与48kHz桌面扬声器/DMIC0已运行；低音量播放退出0，4.86秒非零录音/无削波，空闲PCM关闭/双功放静音 | 实际声音/拾音质量/耳机/DSM/校准/休眠；最新重启自动音频回归继续',
'蜂窝网络/数据':'#109自动MPSS及固件/RAM COW运行，源NV保持；历史QRTR/PD回归保留 | 通话/移动数据未验收；NV不写，冷启动/休眠/长期稳定',
'振动':'AW8697历史电气验收保留；本轮无新脉冲，桌面feedbackd设silent/max-haptic-strength0 | 用户暂缓机械确认；静态分析和日志，保持唯一OF身份'
}
for name,row in rows.items():
    text=re.sub(r'^\| '+re.escape(name)+r' \|.*$', '| '+name+' | '+row+' |',text,flags=re.M)
text=text.replace('下一项优先显示错误关屏状态/DSI下溢及5GHz新启动数据失败，其后2.4GHz HTTP收尾和其它硬件；', '下一项核对Phosh实物显示/触屏、重启音频自动恢复，再查5GHz、显示长稳和其它硬件；')
text=text.replace('保留Android和全部数据。','userdata已按新授权覆盖；GPT/NV/persist及历史离线源保持。')
hardware.write_text(text)
(root/'NEXT-SESSION.md').write_text('''# 继续：持久Phosh系统与剩余硬件

先读[阶段109](sessions/109-pmos-userdata-phosh-and-desktop-audio.md)、[硬件状态](linux-port/docs/HARDWARE-STATUS.md)和[核验](reference/kernel109/checkpoint-validation.json)。用户选择Phosh；全硬件goal active，无预算，不能提前标完成。

'''+intro+'''
实际已部署内核位于`/home/cy122/pmos-samurai-kernel109/kernel`，initramfs同目录`initramfs`；原`/home/cy122/x2pro-linux/linux`和原initramfs仍为#106基线，未覆盖。EDK2位于`/home/cy122/edk2-samurai/repo`，其内嵌DTB与#109 DTB逐字节一致。原rootfs01离线源保持，新#109初始F2FS sparse是console，Phosh及UCM随后安装到真实userdata；不能将初始sparse误称为包含最终桌面的镜像。

运行身份与原始档案只在私人`E:/edk2-samurai-out/kernel109`核对；不要把bootID/SSID/PSK/PIN/固件或原日志写入公开文档。SSH使用`reference/kernel109/usb-ssh-pmos.ps1`，新OpenSSH主机密钥已核验；旧kernel72包装器只适用于旧诊断Dropbear环境。SCP使用同目录scp-pmos.ps1；PIN在私人login-pin-private.txt，仅供本机解锁，SSH仍密钥认证。

1. 核对用户实体画面/触屏反馈。已发送异步问题，请从已有答案继续，别重复询问。截图已成功，但不能据此宣称原滚动花屏永久修复。不要盲目反复开关面板。
2. 第二次正常重启正在检验UCM自动恢复；新boot获取完整dmesg/Phosh/PA/PCM/功放和联网校时状态，用全新目录/前缀导出并校验。初次rootfs持久重启已通过，第二次结果必须按新证据更新文档。
3. Phosh使用greetd初始cy122会话→/usr/local/bin/samurai-phosh-session→/usr/bin/phosh-session；默认登录器是/usr/libexec/phrog-greetd-session。配置/etc/phosh/phoc.ini须755目录/644文件；home配置归UID10000。stevia-schemas已补装，不能只装stevia可执行文件。错误GNOME_SESSION_AUTOSTART_DIR指向全部应用已撤回，原GPU故障日志保留。
4. samurai-radio现在同步运行SAMURAI_WIFI_MANAGED=1，只准备固件/本机地址/MPSS/QRTR/TFTP/NV RAM COW；NetworkManager随后接管WPA和DHCP，usb0保持unmanaged。私有2.4GHz NM配置600，禁止重复启动旧WPA脚本。chronyd依赖networkmanager，已完成NTP校时。
5. 本机UCM在/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro；ASoC FE在PCM open前需要HiFi verb的backend路由，设备EnableSequence单独设置太晚。PulseAudio为桌面音频owner，48kHz/S16LE；不要另外让第二个音频服务抢PCM。短时测试保留原包，实际声音/拾音质量未确认。
6. 继续5GHz认证/数据问题、显示长稳和其余摄像头/SLPI传感器/指纹/GNSS/蜂窝等；保留15组状态，未验收项目不能靠删warning变为通过。蓝牙不配对连接，振动只日志/静态，不发脉冲，NFC仅控制器，充电探针收尾。

持久F2FS日常重启用reboot-pmos-persistent.sh（新prefix、当前bootID），正常OpenRC关机后com-up并等待USB/SSH。旧F1流程在rw根上不重放；本轮一次remount-ro拒绝后已改正常关机。需要刷新内核时重新完整备份、核对分区与候选，DTB变更仍需更新EDK2内嵌DTB。flash-pmos.ps1会erase userdata，不能作仅内核更新或日常重启工具。

所有原始日志/录音/身份/凭据/固件/镜像私人，未提交推送；不运行旧sync-docs-to-repo.sh，不重放旧bootID守卫。USBipd保持Running，EUD每个owner finally关闭/Dispose/detach，hrdevmon警告保留，不forcebind。临时APK CONNECT代理、SSH reverse tunnel和转发规则已关闭，恢复原密钥SSH策略。
''')
(root/'sessions/109-pmos-userdata-phosh-and-desktop-audio.md').write_text('''# 109：userdata F2FS、Phosh 与桌面音频

日期：2026-10-11。用户要求继续适配并刷入userdata，选用Phosh。实际部署Linux #109；全硬件goal active。

'''+intro+'''
## 已构建、刷入与保存

从#106当前源码/初始化目录建立独立kernel109阶段，保留原工作树/全部未跟踪输入与完整boot/logdump/GPT/NV/persist证据。只新增F2FS内建特性、切换独立initramfs来源及SOFEF03F状态修复，BOOT配置、固件boot及DTB不变。

面板DCS错误后仍完成原有22ms/120ms等待与复位、VCI/VDDD断电，返回可使DRM core清理状态的结果，同时记录错误；regulator失败保留持有引用，下次prepare不重复增加引用。以真实函数编译ASan/UBSan错误注入，验证超时后重开/等待/prepare回滚/disable失败引用平衡；W=1面板编译及完整Image/DTB成功。实机单次正常关闭重开恢复0x9c，未出现旧already prepared/enabled错误。

F2FS切根检查唯一userdata身份/容量、文件系统与release标识，先ro,norecovery核验再rw切换。119033245696字节布局已校验；初始sparse462076172字节，2215块，展开重建与F2FS fsck通过。按新授权erase userdata、刷F2FS sparse、刷logdump新Image，各步成功。只替换FAT中的Image并保留samurai.dtb，其它固件不动。原rootfs01未修改。

## 用户态修复

添加loopback 127.0.0.1持久服务；恢复原安装包自带aarch64 APK签名公钥并通过仓库签名检查，未关闭验证。安装Phosh和Mesa。临时loopback CONNECT relay及USB SSH转发用于包下载，安装后规则/通道/helper已关闭。补装stevia-schemas修复缺失mobi.phosh.osk schema；纠正Phosh会话路径、原生Phrog登录器、配置目录、所有权和权限。

一次错误自动启动目录使应用过多并触发GPU fault/恢复，原始日志保留；已移除该目录覆盖。修正后Phosh与Stevia持续运行，1080x2400/scale3截图通过。正常重启保持F2FS测试文件与SSH身份，自动radio/NM/Wi-Fi/Phosh/NTP通过；最新新boot无显示完成超时/GPU fault、taint0。实体显示与解锁触摸仍待用户确认。

原5GHz有界认证失败保留；2.4GHz2462完成关联、DHCP、网关3/3、HTTP577B与HTTPS。NM采用已验证本机地址、关闭扫描随机地址，私有PSK配置600，锁定已通过2.4GHz频段并自动连接；USB不由NM接管。同步radio固件准备完成后才启动NM，避免重复WPA owner。chronyd依赖NM并完成校时。

本机UCM以HiFi verb先建立FE backend，再让设备切换Speaker/DMIC0；只设置Device EnableSequence会导致PA探测PCM时Invalid argument。配置目录755，文件644。PA出现真实48kHz立体声sink与单声道source；2秒低音量paplay退出0，parec有限4.86秒获得233280帧/221056非零/73种值/peak36/无削波。两个PCM和双功放在空闲后关闭/静音，failed0；数字样本不能证明拾音声学质量。

## 验证与边界

[checkpoint-validation.json](../reference/kernel109/checkpoint-validation.json)由实际档案及内嵌SHA校验生成。六LUN geometry/head/tail一致；完整boot与persist保持、当前logdump匹配候选、所有源NV校验通过。公共目录保留可复现脚本、面板补丁与本机UCM；原始档案、固件、镜像、SSID/PSK/PIN及录音全部私人。

新增桌面包和配置写入实际userdata；初始F2FS sparse仍为console。第二次正常重启正在验证新增UCM的自动恢复，结果应追加独立检查点。冷断电/休眠/长稳、5GHz、实体花屏、通话/移动数据、摄像头/SLPI/指纹/GNSS及其它未验收项继续保留，不能提前宣布系统全部硬件可用。

## 外部资料

同平台适配参考[hotdog-linux-bringup](https://github.com/Sr-0w/hotdog-linux-bringup)及其[DSI/DSC传输错误记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-17-dsi-dsc-transport-errors.md)，只用于定位检查方向。本机参数/状态修复依据本机代码与实测；原厂来源见[realme X2 Pro kernel source](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source)。

Phosh包入口见[postmarketOS UI安装说明](https://wiki.postmarketos.org/wiki/Category:Interface)，NM地址/频段行为见[官方Wi-Fi设置文档](https://networkmanager.dev/docs/api/latest/settings-802-11-wireless.html)，本机UCM布局参照[ALSA官方配置仓库](https://github.com/alsa-project/alsa-ucm-conf)。包下载CDN一次TLS失败后，从[Alpine官方镜像名单](https://mirrors.alpinelinux.org/)中的USTC取得同版本包，目标APK继续核验签名。
''')
print('PUBLIC_STAGE109_DOCS_UPDATED_NO_IDENTITIES_OR_CREDENTIALS')
