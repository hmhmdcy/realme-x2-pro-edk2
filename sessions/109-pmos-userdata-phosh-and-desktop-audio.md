# 109：userdata F2FS、Phosh 与桌面音频

历史阶段109；当前部署与用户物理确认见[阶段112](112-startup-sensor-registry-and-reboot.md)。以下保留109当时检查点及未确认边界。

日期：2026-10-11。用户要求继续适配并刷入userdata，选用Phosh。实际部署Linux #109；全硬件goal active。

手机已刷入Linux #109，并从userdata上的F2FS启动postmarketOS/Nura edge；Phosh、屏幕键盘、USB NCM密钥SSH、NetworkManager管理的2.4GHz Wi-Fi和NTP已运行。正常重启后文件、桌面和Wi-Fi自动恢复，HTTPS复测通过；最新启动显示完成超时0/GPU故障0/taint0。实体画面与触屏解锁仍等待用户确认，不能以截图替代光学验收。
SOFEF03F在DCS关闭/睡眠错误后完成物理断电并允许DRM清理状态，regulator引用平衡修复已构建部署；实际函数ASan/UBSan错误路径验证和一次实机正常DRM关闭/重开通过。旧滚动花屏/DSI下溢及5GHz问题继续保留；最新5GHz有界认证尝试失败，2.4GHz已通过网关、HTTP、HTTPS和重启后自动连接。
本机UCM已接入桌面扬声器/DMIC0，应用层2秒低音量播放退出0，有限录音4.86秒/233280帧/221056非零/无削波，空闲后PCM关闭、两只功放静音且failed0。实际声音/拾音质量未获物理确认。一次错误的应用自动启动配置触发GPU恢复，已撤回并保留原日志，修正后的新启动未复现；长稳仍未验收。
用户本轮明确授权覆盖userdata，已执行erase与F2FS sparse刷写；其旧Android/data不再保留。只刷userdata/logdump，boot固件及DTB保持；六LUN头尾/GPT、NV、persist一致，原rootfs01离线源和85–108历史证据保留。蓝牙不配对连接、振动不发新脉冲、NFC仅控制器、充电探针收尾；私人凭据/身份/固件/日志/录音/镜像不公开，不提交推送；全硬件goal active。

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

新增桌面包和配置写入实际userdata；初始F2FS sparse仍为console。第二次正常重启未恢复USB网络，已由F1→fastboot仅重启同镜像恢复；启用boot阶段NCM/SSH与持久rc.log后，第三次正常重启独立核验通过。失败原因和长稳未验收。冷断电/休眠/长稳、5GHz、实体花屏、通话/移动数据、摄像头/SLPI/指纹/GNSS及其它未验收项继续保留，不能提前宣布系统全部硬件可用。

## 外部资料

同平台适配参考[hotdog-linux-bringup](https://github.com/Sr-0w/hotdog-linux-bringup)及其[DSI/DSC传输错误记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-17-dsi-dsc-transport-errors.md)，只用于定位检查方向。本机参数/状态修复依据本机代码与实测；原厂来源见[realme X2 Pro kernel source](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source)。

Phosh包入口见[postmarketOS UI安装说明](https://wiki.postmarketos.org/wiki/Category:Interface)，NM地址/频段行为见[官方Wi-Fi设置文档](https://networkmanager.dev/docs/api/latest/settings-802-11-wireless.html)，本机UCM布局参照[ALSA官方配置仓库](https://github.com/alsa-project/alsa-ucm-conf)。包下载CDN一次TLS失败后，从[Alpine官方镜像名单](https://mirrors.alpinelinux.org/)中的USTC取得同版本包，目标APK继续核验签名。

## 最后实机状态

新增UCM后的第二次正常重启曾运行约370秒而USB网络未恢复；取得F1回执、独立fastboot核验后只reboot同#109，没有新刷写，Phosh/NM/NTP/音频自动恢复。随后把NCM/SSH提前到boot并启用持久rc.log，第三次正常重启与文件/HTTPS/校时/Phosh/UCM空闲关闭回归通过。最新显示完成超时1/GPU故障0/taint0、AW8697 starts0；超时在128.02秒、Phosh启动后出现，最新截图仍成功。那次重启失败原因及显示/重启长稳仍待定位，不能说已彻底解决。已构建审计#110诊断救援候选（不挂userdata、不自动启动radio），尚未部署，当前仍#109。
