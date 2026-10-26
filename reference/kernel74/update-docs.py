from pathlib import Path
import json
import subprocess

w = Path('/mnt/e/RealmeX2Pro edk2')
ref = w/'reference/kernel74'
report = json.loads((ref/'evidence-validation.json').read_text())
assert report['native_boot_handoff_verified'] and report['taint']==0
captures = json.loads((ref/'capture-validation.json').read_text())
boot_id = report['final_boot_id']
log_bytes = captures['final-dmesg']['raw_bytes']
facts_bytes = captures['final-facts']['raw_bytes']
session = '74-sm8150-display-boot-handoff.md'
state = f'''#68已自动完成SM8150显示接管：两次启动完整日志均无SMMU context fault、DSI错误或
vblank WARNING；每次三组彩条—白屏—彩条、九次显示关闭/开启，合计18次通过。
原生SOFEF03F 1080×2400@60 DSC、面板状态0x9c、120/256/400亮度写入保留。
最终boot_id={boot_id}、taint0，{log_bytes}字节dmesg和
{facts_bytes}字节facts通过设备SHA/gzip CRC/长度与实际boot/logdump哈希核对。
本轮四次logdump写入，boot、Android/全部数据/GPT保持。失败#65/#66/#67均归档。
GPU固件七个哈希/分段及MDT loader几何已核对；GPU/GMU仍disabled，尚无渲染验证。
下一项Adreno640/GMU真实渲染，然后电池/充电、无线/音频等；90Hz/休眠仍待验。
'''
for name in ('README.md','RX-CONSOLE.md','FLYWHEEL.md','linux-port/README.md'):
    path = w/name
    text = path.read_text()
    start = text.index('当前硬件接入：')
    end = text.index('\n\n',start)
    prefix = '../' if name.startswith('linux-port/') else ''
    text = text[:start]+f'当前硬件接入：[session74]({prefix}sessions/{session})。\n'+state.rstrip()+text[end:]
    path.write_text(text)
path = w/'HANDOVER-NEXT.md'
text = path.read_text()
start = text.index('## 0. ')
end = text.index('## 2. ',start)
text = text[:start]+'''## 0. TL;DR - where the project stands (2026-10-10, session74)

'''+state+'''
显示交接补丁0010在IOMMU换域前停止本机遗留INTF1自动刷新，等待旧帧结束，
清空旧CTL0图层/INTF/DSC，提交后再次复位以取消等待TE的空kickoff。
最终两次自动启动和18次显示电源循环通过；不再需要手动reprobe或首次电源循环修复。
保留了前三种真机失败；局部CRC通过不能替代完整启动日志。补丁只启用sm8150-dpu，
命令模式已验，video-mode/其它板/实际冷断电/休眠和无缝保留splash未验。

原生面板代码/51条本机命令、GPIO/DSI供电、REFGEN内建/defer60秒与session73相同。
触摸/CPU/三路温度/六UFS/NCM SSH/EUD保持；新F1、原生命令和释放证据均归档。
GPU固件仍只在本地，不入Git；全ELF与分段MDT内容一致，LOAD需4KiB，
本机gpu_mem为8KiB，布局匹配loader，不代表PAS认证、GMU启动或渲染已经通过。
立即回退只需kernel74/logdump-before.img（已验#64），boot仍是session73原生显示版本。

## 1. What to do next, in order

直接交接见NEXT-SESSION.md，复制提示词见NEXT-SESSION-PROMPT.md。

1. 从169.254.42.1密钥SSH获取新boot_id/完整日志，保留#68显示接管基线。
   接入本机Adreno640/GMU和签名固件，验证实际GPU任务/渲染及恢复。renderD128本身
   不能证明GPU成功；DT仍disabled。固件只读提取包在本地kernel73/gpu-firmware-stock.tar。
2. 随后电池/充电、无线/音频等14组功能。保留已有触摸、显示、USB的验收边界。
   显示90Hz/休眠/光学图像和亮度硬件读回、触摸精度、OTG/USB3仍需独立完成。

执行边界：保留Android/全部数据；部署仅boot/logdump；保留TOP_CFG0x11/整帧/
RX53/F1/两终端；串口和对应USB接口单owner并finally释放。实际源码在
/home/cy122/x2pro-linux/linux，initramfs在/home/cy122/x2pro-linux/initramfs。
不要运行旧build-image.sh覆盖真实init。DT变化必须更新实际UEFI固件；源码/证据
仅推fork/master。读分区按PARTNAME核对，不能猜sde编号。

'''+text[end:]
repo = '/home/cy122/edk2-samurai/repo'
head = subprocess.check_output(['git','-C',repo,'rev-parse','--short','HEAD'],text=True).strip()
subject = subprocess.check_output(['git','-C',repo,'log','-1','--format=%s'],text=True).strip()
ahead = subprocess.check_output(['git','-C',repo,'rev-list','--count','origin/master..HEAD'],text=True).strip()
text = text.replace('    master = bd23aaa  samurai: enable automatic USB NCM and public-key SSH',
    f'    master = {head}  {subject}\n             bd23aaa  samurai: enable automatic USB NCM and public-key SSH')
text = text.replace('    102 commits ahead of upstream origin/master',f'    {ahead} commits ahead of upstream origin/master')
path.write_text(text)

(w/'NEXT-SESSION.md').write_text(f'''# 下一阶段交接：Adreno640/GMU（2026-10-10，session74）

当前#68，boot_id={boot_id}、taint0。两次自动启动无SMMU context fault、
DSI错误、vblank WARNING；每次三组A/B/A CRC和九次显示电源循环通过，合计18次。
SOFEF03F 1080×2400@60 DSC、面板0x9c、120/256/400亮度写入保持。
最终dmesg {log_bytes}字节/facts {facts_bytes}字节，设备SHA/gzip CRC/长度均通过。
这只证明已捕获的启动和显示测试；冷断电、90Hz、休眠、光学图像、亮度硬件读回未验。

0010增量补丁实现IOMMU换域前停止INTF1自动刷新、按旧vdisplay等候帧结束（最多50ms）、
关闭TE，清空旧CTL0的LM/INTF/DSC，刷新/提交后再复位，取消等待TE的空kickoff。
仅sm8150-dpu执行。#65启动成功但暖重启vblank失败，#66无start产生iova0 fault，
#67停TE/解除输出后仍有DSI下溢；均保留完整日志，不是成功基线。
#68两次自动启动成功，不要回退为那些中间候选。实际Linux源保留已有EUD/RMI/RPMh补丁。

下一项GPU/GMU。DTS仍disabled，renderD128来自MSM注册，不表示GPU成功。
本机vendor曾以ro,noload挂载提取固件并卸载，本地
E:\\edk2-samurai-out\\kernel73\\gpu-firmware-stock.tar，SHA83df98ec…；专有blob不入Git。
reference/kernel73/gpu-firmware-manifest.json与kernel74/gpu-loader-validation.json
已核对七文件哈希、ELF/分段/metadata相等、可重定位LOAD需4KiB，gpu_mem
0x99515000+0x2000足够。可以保留全ELF内容按板级firmware-name命名，但PAS认证、
GMU启动和实际渲染必须真机验证。不要使用其它板的签名zap固件。
主线a640.1使用a630_sqe.fw/a640_gmu.bin，优先核对板级供电/OPP/内建依赖后接入。

SSH用reference/kernel72/usb-ssh.ps1，169.254.42.1/16；SCP用scp-usb.ps1（-O）。
本地客户端私钥/known_hosts在kernel72，手机主机身份跨重启保留；别改默认路由。
Windows系统UsbNcm自动APIPA；服务以实际密钥认证为准。重启后先eudtool com-up，
再用新F1前缀与有界fastboot枚举确认；最终COM14在Windows Shared/未Attached、
相关五PnP节点OK，所有任务连接owner已释放。

实际内核/home/cy122/x2pro-linux/linux；真实initramfs在/home/cy122/x2pro-linux/initramfs，
保留init/USB hook/SSH身份，别运行旧build-image.sh。保留REFGEN=y/defer60秒。
本轮未改DTS、面板、配置、UEFI或boot，只四次logdump部署；同镜像复测只reboot。
已部署kernel74/logdump-k74-drain.img：8e43d13658a1d332c441f68a6008e7ebb855177b59fbeb447a196195239f1ee5。
boot仍kernel73/boot-k73-display.img：57508887131ae55cf9465fa1a44280fa45b507a3439345ffe635dc7544eaa999。
实际分区哈希在final-facts；按PARTNAME查找，本机logdump=/dev/sde32、boot=/dev/sde11。
立即回退只刷kernel74/logdump-before.img（c7778d45…），保留当前boot。
仅boot/logdump、保留Android/全部数据/GPT、TOP_CFG0x11/整帧/RX53/F1/两终端，
单owner/finally释放，只推fork/master。全硬件目标仍active，GPU后推进电池/充电等。
''')
(w/'NEXT-SESSION-PROMPT.md').write_text('''继续无人硬件接入目标。先读NEXT-SESSION.md、sessions/74和reference/kernel74/README.md。
当前#68显示接管已在两次启动与18次显示电源循环验证，无SMMU/DSI/vblank警告、taint0；
原生60Hz DSC/CRC、NCM SSH169.254.42.1、触摸/CPU/UFS/EUD保持。接下来接入本机
Adreno640/GMU并验证实际渲染；GPU仍disabled，renderD128不能当成功证据。
本地kernel73/gpu-firmware-stock.tar与kernel74/gpu-loader-validation.json已核对七固件哈希、
ELF分段/metadata及4KiB LOAD符合8KiB carveout，但PAS/GMU/渲染仍待真机验证。
保留0010显示接管补丁、真实WSL Linux/initramfs/init/USB hook与本地SSH身份，
不用其它板签名blob，不发布专有固件，不运行旧build-image.sh。REFGEN内建/defer60秒保留。
DT变更需进入实际UEFI固件，按PARTNAME核对分区；只写boot/logdump，保留Android/全部
数据/GPT、TOP_CFG0x11/整帧/RX53/F1/两终端，owner finally释放，只推fork/master。
GPU后电池/充电、无线/音频等；90Hz/休眠/光学与亮度读回及其它硬件仍待验。
''')
path = w/'DOCS-INDEX.md'
text = path.read_text().replace('| sessions/73-native-sofef03f-dsi-dsc-display.md、reference/kernel73/ |',
    '| sessions/74-sm8150-display-boot-handoff.md、reference/kernel74/ | DPU5命令显示接管、失败迭代、两启动/18次电源循环与GPU loader预检 |\n'
    '| sessions/73-native-sofef03f-dsi-dsc-display.md、reference/kernel73/ |',1)
text = text.replace('session73当前原生显示状态、启动SMMU与GPU接入、自动USB SSH通道与短提示词',
    'session74显示交接验证、GPU/GMU接入、自动USB SSH通道与短提示词')
path.write_text(text)
path = w/'linux-port/docs/HARDWARE-STATUS.md'
text = path.read_text().replace('（2026-10-10，session73）','（2026-10-10，session74）')
start = text.index('本轮#64')
end = text.index('| 功能组',start)
text = text[:start]+f'''本轮#68/taint0、两次自动启动与18次显示电源循环、六组A—B—A硬件CRC通过。
显示接管SMMU fault及候选DSI/vblank故障已在最终两次完整日志中消失；
{log_bytes}字节dmesg和{facts_bytes}字节facts/实际分区哈希通过。GPU仍未启用。
详见sessions/74/reference/kernel74；原生面板、触摸、USB证据见sessions/73、71、72。

'''+text[end:]
text = text.replace('两启动各三次电源循环及亮度写入通过 | 首次接管SMMU fault、90Hz、',
    '显示接管、两启动18次电源循环及亮度写入通过 | 冷断电、90Hz、')
text = text.replace('| GPU | 设备树禁用，未验收 |',
    '| GPU | 设备树禁用；本机七固件哈希/ELF/MDT LOAD几何通过预检，运行未验收 |')
text = text.replace('优先显示交接/GPU、','优先GPU/GMU、')
path.write_text(text)
print('Updated living documentation from successful device evidence; historical sessions preserved.')
