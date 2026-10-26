from pathlib import Path
import json,shutil
root=Path('/mnt/e/RealmeX2Pro edk2');ref=Path(__file__).resolve().parent
nextfile=root/'NEXT-SESSION.md';old=nextfile.read_bytes();assert '阶段189' in old.decode()
archive=root/'archive/NEXT-SESSION-through189-2026-10-15.md';assert not archive.exists();archive.write_bytes(old)
text='''# Realme X2 Pro 当前检查点

最后核对：2026-10-15，阶段190，完整外设goal active。GPS辅助能力发现修复已部署并实机对照；有效fix尚未获得。内核/传感器保持189组合及同一启动，当前通过严格原密钥的Wi-Fi管理，USB NCM新传输故障未修复。规则见[边界](WORKING-BOUNDARIES.md)。用户暂无耳机，不重复问。

## 当前部署与实机依据

| 项目 | 最后核对 |
| --- | --- |
| 基础组合 | kernel183/logdump183、boot/DTB172；modules132覆盖hci_uart185及fastrpc189两项，Mesa149/UCM173 |
| GPS修复190 | ModemManager同一LOC事务实际先indication后ACK；补丁后SupportedAssistanceData从0变1/XTRA，服务器0变3，未伪造能力位。23个实际C回调场景、ASan/UBSan、原版与破坏变体负例通过 |
| 当前4216.59秒 | 同189第二新boot、taint0，ADSP/SLPI/modem running、SensorProxy三项Has为1。修复MM程序运行、GPS关闭/刷新30秒、SIM缺失/无bearer；190所列故障增量0，保留全boot蓝牙重组1 |
| GPS标准接口 | 无SIM时Setup(6,false)成功，125.93秒131条不同NMEA/校验全通过；有效GGA/RMC为0、raw0、C/N0数值0，最多12颗in-view不等于跟踪。结束Setup0/刷新恢复 |
| 传感器189 PM | 连续实际45.2784/45.2053/45.2838秒，success3/fail0/RTC3、7266 callbacks err0；醒后四项CLI正常disable、daemon/proxy身份保持，之后真实active Wayland UID10000 Claim/Release通过 |
| USB190 | 归档1933312/1958876字节时传输中断；UDC configured/carrier1/原IPv6仍在。Windows重启网卡拒绝访问。Wi-Fi严格原密钥/同boot恢复管理，一次gadget解绑/绑定后configured，但NCM恢复无正向证据；未重启手机 |

依据：[190](reference/kernel190/README.md)、[MM部署](reference/kernel190/mm-deployment-validation.json)、[真机提前完成](reference/kernel190/mm-native-validation.json)、[USB后最终状态](reference/kernel190/post-usb-validation.json)。[189检查点逐字快照](archive/NEXT-SESSION-through189-2026-10-15.md)，相对链接按工作区根解释。

## 源码、产物与回退依据

- ModemManager固定提交7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a，与安装版及Alpine归档SHA512匹配。补丁[LOC提前轨道源完成](reference/kernel190/modemmanager-loc-early-orbit-source.patch)先监听、保存提前boxed输出、校验ACK、分别持有GTask引用并取消已完成监听/超时；其余LOC操作尚未修复。
- 当前/usr/bin/ModemManager SHAfbc4084873e8e79d4bcdfa37982f4016a9e898f7123cecd37ba941ed55f27f69；原件4d5a8258…在手机k190-mm-deploy/ModemManager.original及主机E:/edk2-samurai-out/kernel190。SDK仅提取已验证签名APK，未安装系统包；APK DB/系统库/插件保持，候选构建RPATH已清除。激活文件原样恢复，SetLogging INFO成功。本地覆盖仍需正式入包，更新会覆盖。
- WSL内核/home/cy122/pmos-samurai-kernel136/kernel tracked14：原183的12源、hci_qca185、fastrpc189。FastRPC源41c8db5c…/模块88553112839d0a23604171edb03004a15e94f7cc3b174ebb3b9f2e56d3cc2fcc，hci_uart185 f6c5ed35…；Image/DTB/config保持，完整Module.symvers16793行/modules.order770项恢复。
- FastRPC189用TASK_INTERRUPTIBLE|TASK_FREEZABLE及冻结重试；52个等待函数stub场景、ARM64 W=1告警0及三轮真PM通过。普通信号/freezer伪信号竞态仍开放，Qualcomm v3提案未直接应用。原模块4515b1b2…及原源a15e99ea…在189完整备份；不要强制卸载使用中的模块。
- SSC服务固定1902…文件服务、184独立libssc和每boot一次启动门控，303个来源/24固件文件只复制到私人RAM。A.11独立路径/lib/firmware/qcom/sm8150/realme/samurai-a11-r187；原00121保留。当前持续服务不要盲目stop/start，186共享池−22未解决。
- 当前启动身份手机k189r2-reboot-runtime/boot-id-private.txt。190 host.py优先用私人wifi-current-endpoint-private.json，严格HostKeyAlias/原公钥；旧USB scope记录保留，不能据旧连接假设发生了重启。下一boot重新只读确认身份/端点，再执行切换。
- 190主私人归档SHA461318d5…/322文件及原新程序已下载核验；USB补充SHAe4bb35dd…也核验。USB不完整副本保留。189原完整归档7f80cdca…、重要分区/NV/校准备份不变。固定BDS164/固件172/FdtBlob129及183/181回退保持。

## 续作与已知风险

1. 优先审查MM同文件Inject XTRA Data的ACK后监听，以及Inject UTC Time/Position的独立异步引用生命周期，再做完整轨道注入/有效期确认、UTC/标准GPS与GeoClue回归。当前只修复能力发现；不要将新注册事件路径未经测试当作完成。
2. UTC一次注入ACK/status0、CID释放成功，但首次脚本用了不存在的close，清理失败/截止/进程1保留；后续脚本已改close_async，尚不能把首次记为完整通过。TLS全局轨道50413字节已下载，尚未注入；注入前重新确认有效数据。GeoClue/MM原本支持SIM缺失的独立GPS，不需要绕过授权或冒用Phosh；定位测试应排除其它提供者混入。
3. USB双向IPv6不通但手机同boot/无所列kernel故障；一次NCM gadget重绑没有正向恢复证据。当前Wi-Fi管理正常，继续调查实际USB数据/邻居链路；Windows适配器复位拒绝访问不等于手机崩溃。曾误读磁盘表格，已复核E盘约80GB可用，没有删除或迁移材料。
4. 189第2轮Wi-Fi35秒未关联，后来经过第3轮PM才恢复，不能称自行恢复。当前BT phase5/3.2Mbps/chunk13/partial0/firstff重组1与185旧phase2前导00不同，继续修复；按边界只扫描。
5. FastRPC普通信号/freezer竞态、186共享池stop/start/reclaim−22/SSR及传感器人工运动/方向/亮暗/精度、跨boot/冷启/长稳开放。失败SCM原型ba187458…源/95c9e2b0…模块不能当修复；实际VMIDs3/5/6，勿试遍未知owner或隐藏错误。
6. 蜂窝仍sim-missing，注册/数据/通话/SMS无业务验收；实体camera PM8008四输入/冷地址/复位/chip-enable、CCI/C-PHY和真实出图未解决，内部TPG不是实体摄像头。其它见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。

导航：[会话索引](sessions/INDEX.md)、[文档索引](DOCS-INDEX.md)。
'''
assert len(text)<=6500,len(text);nextfile.write_text(text)
path=root/'linux-port/docs/HARDWARE-STATUS.md';content=path.read_text();lines=content.splitlines()
assert lines[2].startswith('用途：')
lines[2]='用途：当前硬件验收清单。最后核对：2026-10-15，阶段190。ModemManager提前LOC完成竞态修复已部署，XTRA能力0→1/服务器0→3，真实GPS fix仍无；4216.59秒同189 boot/taint0，三个DSP与SensorProxy保持。内核仍183/logdump183、boot/DTB172，modules132覆盖hci_uart185/fastrpc189，Mesa149/UCM173；189传感器三轮PM范围保持。新USB传输故障尚未证明恢复，当前严格原密钥Wi-Fi管理。见[190](../../reference/kernel190/README.md)、[189](../../reference/kernel189/README.md)。完整外设goal active；规则见[边界](../../WORKING-BOUNDARIES.md)。'
for i,line in enumerate(lines):
 if line.startswith('| GNSS定位 |'):
  lines[i]='| GNSS定位 | 190修复并部署MM提前完成竞态，实际indication先于ACK仍正确得到XTRA/3服务器；标准Setup无SIM可用，131条NMEA校验通过；一次UTC完成status0 | NMEA仍无有效GGA/RMC/raw/CNR；真实fix、完整轨道注入/有效期、UTC与位置异步生命周期及GeoClue/精度/冷热启待验收。首次UTC脚本清理失败保留；仅有in-view数量不是卫星锁定 |'
 if line.startswith('| 普通USB与OTG |'):
  lines[i]='| 普通USB与OTG | USB 2.0 Type-C；历史NCM/SSH/SCP与EUD共存；190手机同boot、UDC configured，Wi-Fi严格原密钥恢复管理 | 190 USB归档尾部中断、双向IPv6探测不通，单次gadget重绑后恢复无正向证据；Windows网卡复位拒绝访问。NCM稳定性、OTG/角色切换/冷启/PM及EUD接收/退出路径待验收；USB3不是本机目标 |'
path.write_text('\n'.join(lines)+'\n')
readme=ref/'README.md';readme.write_text(readme.read_text().replace('131种不同且校验有效的NMEA句子','131条内容不同且校验有效的NMEA句子'))
log=(Path('/mnt/e/edk2-samurai-out/kernel190/rebind-usb-gadget-once-host-private.log')).read_text().splitlines()[0]
(ref/'usb-rebind-validation.json').write_text(json.dumps(json.loads(log),indent=2)+'\n')
print('Stage190 checkpoint updated; previous stage archived verbatim; characters:',len(text))
