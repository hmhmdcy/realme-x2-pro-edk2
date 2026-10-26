from pathlib import Path
import json, subprocess
w=Path('/mnt/e/RealmeX2Pro edk2');r=Path('/mnt/e/edk2-samurai-out/kernel71')
v=json.loads((r/'input-validation.json').read_text());assert v['basic_touch_pass']
p=w/'sessions/71-native-s3706-touch-bringup.md';s=p.read_text()
s=s.replace('完整事件与结果待采样结束后导出并填入此处。','''采样已自然结束，ps未发现capture进程；event-errors为空。
306744字节/12781个24字节ARM64 input_event记录，gzip43740字节，手机与主机
SHA256/gzip CRC/长度全通过，原文SHA为
13930452eea095ae66fb47b278c513bceafa7d2583a09be94fafc00f11d9bfcf。

970个SYN_REPORT，241个tracking contact均有release，末尾active=0；223个contact
发生移动，BTN_TOUCH按下/抬起各69次。记录中最多同时5个contact，553帧有两个及
以上触点；x146–1047/y572–2224，均在1080×2400配置内，活动跨度30.239秒。
因此基本输入通路（点按/移动/释放/多点）已验证，不只是input设备注册。用户确认
操作不是严格的触点数量/边缘标定：不能把最多5个记录触点自动称为五指精度验收，
也尚未做长时间/休眠恢复/方向及边缘校准。数字是实际事件记录，不是补出的EUD文字。''')
p.write_text(s)
p=w/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text()
s=s.replace('当前有14类原生功能需要接入或验收','清单共14类原生功能，本轮触摸基本输入已打通，其余13类仍需接入或验收')
s=s.replace('点按/滑动/双指事件正在采样','设备保存的306744字节真实事件已校验，点按/移动/释放/多点通路通过')
s=s.replace('本轮驱动/总线/供电/DTS已部署，S3706A/F01/F12/event2注册 | 核对真实点按、移动、抬起、双指；休眠/唤醒与长期稳定性',
 '本轮驱动/供电/DTS已部署，S3706A/F01/F12/event2注册；真实点按/移动/释放/多点通路通过 | 触点数量/方向/边缘校准，休眠/唤醒与长期稳定性')
s=s.replace('优先顺序是完成触摸实际输入验收，然后普通USB可靠传输/SSH','触摸基本输入已通过；接下来优先普通USB可靠传输/SSH')
p.write_text(s)
p=w/'HANDOVER-NEXT.md';s=p.read_text();start=s.index('## 0. ');end=s.index('## 2. ',start)
new='''## 0. TL;DR - where the project stands (2026-10-10)

Linux现在进入initramfs用户态，当前是真机内核#61。**本轮实际接通了原生触摸**：
GENI/GPI DMA/RMI4内建、本机DTS/供电及reset GPIO补丁已经部署到boot/logdump。
设备报告S3706A、fw3078696，F01/F12绑定；用户点按/滑动后取得完整输入事件，
基本点按、移动、释放和多点通路通过。屏幕仍显示诊断控制台，触摸不会让现有画面
滚动或变成GUI；原生显示面板/GPU尚未接入。

当前证据是sessions/71-native-s3706-touch-bringup.md、reference/kernel71。
初始完整dmesg54413字节、后续日志见该会话，设备保存后压缩导出并逐项校验。
event2原文306744字节/12781记录通过SHA/gzip CRC/长度，970个SYN_REPORT，
241个contact全部释放，坐标在1080×2400内；记录最多5触点，但不是严格五指/精度
验收。当前boot_id=a31c1158-fbca-4515-83ac-1a3b40ee808e、taint=0。

已有基础能力是UEFI、六个UFS LUN、CPU三个调频policy和CPU7最高2956800kHz表、
三路PMIC温度、simpledrm帧缓冲、EUD交互及F1。除触摸基础通路外，按用户功能
分组还有13类待接入/验收，详见linux-port/docs/HARDWARE-STATUS.md。
普通USB的HS PHY/DWC3/UDC已绑定，但gadget目录为空，尚无USB网络/SSH；
Wi-Fi/GPU/DSP等也还不是可用系统。完整postmarketOS/rootfs没有安装，保留的
64MiB logdump新镜像空闲36605952字节，尚无证明安全的大持久rootfs位置。

历史修复：session66是调频/ADC/earlycon，67是HS PHY，68是实际固件DTB/CPU7 OPP，
69是USB/EUD协调审查，70把PM8009警告降为P3并查清触摸接线，71完成触摸实现。
RPMh读回-95、PM8009、QMP/aux_bridge等仍按影响范围排优先级，没删节点静音。
EUD TX仍可能缺帧，session65有确证；本轮成功校验导出不等于EUD已无损。

## 1. What to do next, in order

直接交接见NEXT-SESSION.md，复制提示词见NEXT-SESSION-PROMPT.md。

1. 核实手机当前模式和连接owner，读session71及校验日志，承接已经部署的#61。
   本轮最后COM14交回Windows、Shared/未Attached，三节点OK、owner释放；以新会话
   的实时枚举/新回执确认，不依据旧截图或PID单独判断系统模式。
2. 优先把普通USB变成可实际传输日志的网络/SSH通道。现有UDC存在但无gadget函数；
   先明确configfs函数与内建配置，再做小范围实现、构建、上机和电脑端真实流量验收。
   实际glue是dwc3-qcom-legacy，EUD与普通USB共存尚未证明；不要预设它一定互斥。
3. 随后推进本机SOFEF03F原生面板/DSI/DSC和GPU，电池/充电，再无线、音频及其它
   功能。优先现有主线/维护者实现和Realme本机源码；每轮交付实现和真实结果。
   触摸后续补方向/边缘/触点数量及休眠恢复验收，不能把目前基本输入当全面完成。

执行边界集中在这里：保留Android/全部数据；刷机仅boot/logdump；现有EUD读取工具
与TOP_CFG0x11/整帧/RX53/F1/原生兼容终端保持，串口/USB一个owner并finally释放。
真实initramfs在/home/cy122/x2pro-linux/initramfs，实际内核在/home/cy122/x2pro-linux/linux；
设备树要更新实际UEFI固件，FAT-only不会激活。结论/源码增量仅推fork/master。
这些是部署边界；当前工作重点是继续实现和验收硬件，不是恢复历史EUD实验序列。

'''
s=s[:start]+new+s[end:]
head=subprocess.check_output(['git','-C','/home/cy122/edk2-samurai/repo','rev-parse','--short','HEAD']).decode().strip()
ahead=subprocess.check_output(['git','-C','/home/cy122/edk2-samurai/repo','rev-list','--count','origin/master..HEAD']).decode().strip()
import re
s=re.sub(r'(?m)^    master = .*$',f'    master = {head}  samurai: audit PM8009 resource scope and native touch prerequisites',s)
s=re.sub(r'(?m)^    \d+ commits ahead of upstream origin/master',f'    {ahead} commits ahead of upstream origin/master',s)
p.write_text(s)
for name in ('README.md','RX-CONSOLE.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/00-INDEX.md'):
 p=w/name;s=p.read_text();s=s.replace('真实输入事件验收见session71；其它硬件仍按清单推进。','306744字节真实事件校验通过，点按/移动/释放/多点通路已验；其它13类功能仍待推进。');p.write_text(s)
print('Hardware progress, input evidence and living handover finalized.')
