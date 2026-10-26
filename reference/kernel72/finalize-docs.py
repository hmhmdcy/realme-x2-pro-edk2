from pathlib import Path
import re

w=Path('/mnt/e/RealmeX2Pro edk2')
boot='5ecfab9e-fa56-4ead-acf8-a5147904980e'
current='''当前硬件接入：[session72]({prefix}sessions/72-usb-ncm-and-autonomous-ssh.md)。
普通USB NCM/密钥SSH/SCP已实现并部署到#62，Windows系统UsbNcm与EUD共存。
部署前后双向4MiB SHA校验通过、错误计数0；另一次重启无需host com-up就能SSH认证。
最终53594字节dmesg和2285字节facts校验通过，taint=0；原触摸/CPU/UFS保留。
本轮仅刷一次logdump，Android/全部数据、boot固件、EUD/RX53/F1/两终端保留。
下一项原生显示/GPU；触摸精度、OTG及其它硬件仍须接入/验收。
'''
for name in ('README.md','RX-CONSOLE.md','FLYWHEEL.md','linux-port/README.md'):
    p=w/name; text=p.read_text()
    prefix='../' if name.startswith('linux-port/') else ''
    text=re.sub(r'当前硬件接入：.*?无新EUD实验。\n',current.format(prefix=prefix),text,count=1,flags=re.S)
    p.write_text(text)
p=w/'HANDOVER-NEXT.md'; text=p.read_text()
start=text.index('## 0. TL;DR'); end=text.index('## 2. Verified hardware facts')
text=text[:start]+f'''## 0. TL;DR - where the project stands (2026-10-10, session72)

手机运行Linux **#62**，本轮普通USB网络/SSH已从空gadget推进到真实可用。
NCM以Windows系统UsbNcm驱动工作，EUD/COM14共存；部署前后各一对4MiB随机文件
SHA256全部通过、收发错误0。独立同镜像重启后，没有host com-up仍可枚举和认证SSH。
最终boot_id={boot}、taint=0，53594字节完整dmesg和2285字节facts
经设备保存、SSH/SCP导出、设备SHA/gzip CRC/长度校验。证据见sessions/72、reference/kernel72。

实际initramfs仅在原configfs挂载后加异步USB hook，并加入静态公钥SSH/PTY支持。
客户端私钥留本地，唯一手机主机私钥仅在本地initramfs/构建目录；都未入Git。
内核配置只修改initramfs UID/GID映射以正确打包root权限；EUD/RMI/DTS/DTB哈希不变。
仅刷一次logdump，boot仍为session71触摸固件，Android和全部数据保留。

已有基础能力：UEFI、六个UFS盘、三CPU policy与CPU7最高2956800kHz表、三路PMIC
温度、simpledrm、EUD/F1、S3706A基本触摸，以及本轮NCM/SSH/SCP。
屏幕仍是诊断控制台，原生SOFEF03F面板/DSI/DSC与GPU尚未接入；没有完整桌面/rootfs。
OTG/USB3/休眠恢复、触摸精度/触点数量等还没验收，整体硬件目标仍在进行。
logdump FAT空闲36016128字节（约34.35MiB），大持久rootfs位置仍未证明安全。

旧RPMh读回-95、PM8009、QMP/aux_bridge等按影响范围保留，没有删节点静音。
Windows单次F1仍会无回执，WSL原工具F1保留；EUD偶发TX缺帧没有被本轮宣称修复。
下一轮应通过新的普通USB SSH通道获取完整内核日志，优先继续硬件实现。

## 1. What to do next, in order

直接交接见NEXT-SESSION.md，复制提示词见NEXT-SESSION-PROMPT.md。

1. 优先通过169.254.42.1的密钥SSH取得新的boot_id/taint/完整dmesg；自动NCM/SSH
   已实测，Windows无额外驱动/网络配置。EUD回到Windows Shared/未Attached，无host owner。
2. 推进本机SOFEF03F原生面板/DSI/DSC与Adreno/GMU，搜索主线/维护者和Realme本机
   实现，按供电/时钟/固件和真实图像数据流验证。随后电池/充电、无线/音频及其它功能。
3. 触摸补方向/边缘/严格触点数量/休眠恢复；USB补OTG/休眠/长期稳定性，不把当前
   设备模式NCM成功扩大成全部USB功能完成。

执行边界：保留Android/全部数据；部署仅boot/logdump；保留既有TOP_CFG0x11/整帧/
RX53/F1/两终端，串口/对应USB接口单owner并finally释放。实际源码在
/home/cy122/x2pro-linux/linux，initramfs在/home/cy122/x2pro-linux/initramfs。
本轮真实init加入USB hook，其余逻辑逐字保留；不要运行旧build-image.sh覆盖它。
DT变化必须更新实际UEFI固件，FAT-only不会激活；源码/证据仅推fork/master。

'''+text[end:]
text=text.replace('Which ordinary USB gadget function/configuration will provide reliable\n  network/SSH on this Windows host, and how will actual USB/EUD role signaling\n  behave? UDC exists; configured functions and real traffic are missing.',
                  'How should USB OTG, suspend/resume and long-term stability be enabled and verified?\n  CDC NCM/SSH/SCP with Windows UsbNcm and EUD coexistence now work; USB3 remains unverified.')
text=text.replace('about34.91MiB free','about34.35MiB free')
p.write_text(text)
p=w/'linux-port/docs/HARDWARE-STATUS.md'; text=p.read_text()
text=text.replace('（2026-10-10，session71）','（2026-10-10，session72）')
a=text.index('按用户能使用的功能分组'); b=text.index('| 功能组')
text=text[:a]+'''按用户能使用的功能分组共14类。触摸基本输入与普通USB NCM/SSH/SCP已打通；
这些组内仍有精度、OTG、休眠等待验，其余功能需继续板级接入和真实数据流验证。
本轮#62/taint0，设备保存53594字节完整日志通过SHA/CRC/长度；同镜像重启无需
host com-up也能认证SSH，双向4MiB随机文件部署前后全部校验通过。详见sessions/72。

'''+text[b:]
old='| 普通USB与OTG | HS PHY、DWC3/UDC已绑定；没有gadget功能，主机模式未接入 | 普通USB实际传输、USB网络/SSH、EUD协调、角色切换/外设 |'
new='| 普通USB与OTG | CDC NCM/high-speed、Windows系统UsbNcm、自动密钥SSH/SCP及EUD共存已实测，双向4MiB校验通过 | OTG/外设、USB3、休眠恢复和长期稳定性 |'
assert old in text; text=text.replace(old,new)
text=text.replace('触摸基本输入已通过；接下来优先普通USB可靠传输/SSH、原生显示/GPU、',
                  '触摸基本输入、普通USB NCM/自动SSH与文件传输已通过；接下来优先原生显示/GPU、')
p.write_text(text)
(w/'NEXT-SESSION.md').write_text(f'''# 下一会话交接：原生显示/GPU（2026-10-10，session72结束）

手机运行#62，boot_id={boot}、taint=0。本轮实现并部署普通USB
CDC NCM/自动公钥SSH/SCP，Windows系统UsbNcm工作且EUD共存，设备协商high-speed。
部署前后双向各4MiB随机文件通过SHA，错误0；独立同镜像重启无需host com-up也可
认证SSH。完整53594字节dmesg、2285字节facts已按设备SHA/gzip CRC/长度校验。
只刷一次logdump，boot仍为session71触摸固件，Android/所有数据/GPT保留。

手机USB地址169.254.42.1/16，电脑自动APIPA；无需改主机默认路由或换驱动。
本地专用SSH私钥：E:\\edk2-samurai-out\\kernel72\\id_ed25519；known_hosts同目录。
日常命令用reference/kernel72/usb-ssh.ps1，SCP用scp-usb.ps1（显式-O）。
手机主机身份跨重启保留，私钥只在本地实际initramfs/构建目录；两份私钥都未入Git。
COM14最后Windows/Shared/未Attached，9501/9500/9505及NCM节点OK，无host连接owner。
第一次在NCM枚举刚出现时SSH未就绪，之后认证成功；等真实回执，不能以PnP等同服务就绪。

下一项推进本机SOFEF03F原生面板/DSI/DSC及GPU/GMU。首先通过新的SSH通道保存完整
日志和显示/固件状态，检索Realme 19781本机源码及主线维护者实现，然后完成板级
供电/时钟/固件/数据流的实现、构建、boot/logdump部署与验收。之后电池/充电、
无线/音频等。当前屏幕仍是UEFI帧缓冲诊断控制台，未安装完整GUI/rootfs。
触摸保留S3706A基本点按/移动/释放/多点证据；精度/方向/严格触点数/休眠尚未验。
USB本轮证明设备模式/NCM/SSH，OTG/USB3/休眠恢复尚未验。不要声称全硬件已完成。

实际内核/home/cy122/x2pro-linux/linux；实际initramfs/home/cy122/x2pro-linux/initramfs。
真实init仅增加configfs后的异步samurai-usb hook，其余EUD逻辑逐字保留；不要运行
旧build-image.sh。内核配置只改INITRAMFS_ROOT_UID/GID=1000以打包root权限。
EUD/earlycon/RMI I²C/DTS/DTB哈希不变。代码：linux-port/scripts/samurai-usb.sh及
build-dropbear-usb.sh；实测/源码/打包核对在sessions/72与reference/kernel72。
logdump-k72-ncm-ssh.img的SHA为13a8263dac6c75f909b6fa8dc89520949c7009ddcb9de2b2a5f6125e26d4292b。
立即回退是E:\\edk2-samurai-out\\kernel71\\logdump-k71-touch.img；boot不用回退。
logdump仍只有约34.35MiB空闲，未确定安全的大持久rootfs位置。

执行边界：保留Android/所有数据，只部署boot/logdump；保留TOP_CFG0x11/整帧/RX53/
F1/两终端，接口单owner并finally释放，只推fork/master。Windows单次F1无回执仍有
记录，既有WSL方法有新F1回执/独立fastboot确认；不恢复旧EUD参数实验。
本輪日期解析/过早枚举查询的失败记录保留并明确废弃错误elapsed字段。
''')
(w/'NEXT-SESSION-PROMPT.md').write_text('''继续无人硬件接入目标。先读NEXT-SESSION.md、sessions/72和reference/kernel72。
当前#62已经有普通USB NCM/自动密钥SSH/SCP，可用169.254.42.1获取完整日志；
无需host com-up的重启/SSH已实测，EUD共存，双向4MiB校验通过。下一项本机
SOFEF03F原生显示/DSI/DSC和GPU，之后电池/充电、无线/音频等。保留Android/所有
数据，仅boot/logdump，保留EUD/RX53/F1/真实init，单接口owner并finally释放，
只推fork/master。不要运行旧build-image.sh，不把USB设备模式或触摸基本通路称为全面验收。
''')
p=w/'DOCS-INDEX.md'; text=p.read_text(); needle='| sessions/71-native-s3706-touch-bringup.md、reference/kernel71/ |'
text=text.replace(needle,'| sessions/72-usb-ncm-and-autonomous-ssh.md、reference/kernel72/ | CDC NCM/密钥SSH自动启动、双向4MiB校验、EUD共存及仅logdump部署 |\n'+needle,1)
text=text.replace('session71结束状态、触摸真机进展、后续USB/显示实作与短提示词','session72结束状态、自动USB SSH通道、后续原生显示/GPU实作与短提示词')
p.write_text(text)
for name in ('sessions/72-usb-ncm-and-autonomous-ssh.md','reference/kernel72/README.md'):
    p=w/name; text=p.read_text().replace('independent-ssh-facts.txt','independent-ssh-ready-facts.txt')
    p.write_text(text)
print('Updated current status, hardware matrix, handover and next-session documents.')
