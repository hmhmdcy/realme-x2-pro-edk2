from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2');path=root/'NEXT-SESSION.md';old=path.read_bytes();assert '阶段190' in old.decode()
archive=root/'archive/NEXT-SESSION-through190-2026-10-15.md';assert not archive.exists();archive.write_bytes(old)
lines=old.decode().splitlines();result=[]
for line in lines:
 if line.startswith('最后核对：'):
  line='最后核对：2026-10-15，阶段191，完整外设goal active。GPS轨道完整注入和LOC异步引用修复已部署，固件有效期0→168小时；有效fix仍未获得。kernel183及189传感器组合/同一启动保持，当前严格原密钥Wi-Fi管理，USB NCM190故障未证明恢复。规则见[边界](WORKING-BOUNDARIES.md)。用户暂无耳机，不重复问。'
 elif line.startswith('| 当前4216.'):
  line='| 当前5871.48秒 | 同189第二新boot、taint0，ADSP/SLPI/modem running、SensorProxy三项Has为1；MM191程序运行、GPS关闭/刷新30秒、MM报告sim-missing/无bearer。191所列故障增量0，保留全boot蓝牙重组1 |'
 elif line.startswith('| GPS标准接口 |'):
  line='| GPS回归191 | 真实50406字节/50分片注入约0.801秒，49次indication先于ACK；固件有效期0→168小时。随后300.5578秒/303条NMEA全校验通过，但有效GGA/RMC/raw/CNR字段均0；GSV最多13颗in-view不等于跟踪。旁路16条SV事件均缺省卫星列表，CID/设备清理通过 |'
 elif line.startswith('依据：'):
  line='依据：[191](reference/kernel191/README.md)、[完整注入核验](reference/kernel191/assistance-end-to-end-validation.json)、[257场景](reference/kernel191/loc-injection-host-validation.json)、[五分钟](reference/kernel191/mm-location-stream-validation.json)、[最终](reference/kernel191/final-validation.json)。[190逐字快照](archive/NEXT-SESSION-through190-2026-10-15.md)，相对链接按工作区根解释。'
 elif line.startswith('- ModemManager固定提交'):
  line='- ModemManager固定提交7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a，与安装版本/官方Alpine源归档匹配；190能力发现修复保持，191[注入补丁](reference/kernel191/modemmanager-loc-injection-order.patch)覆盖UTC/位置/Predicted Orbits/XTRA四路径。ACK持独立GTask引用、提前完成保存、双阶段校验、分片匹配和回退清理。257生产回调场景/ASan/UBSan/4原版失败/3破坏变体通过；原生覆盖XTRA回退，Predicted成功路径只模拟通过。'
 elif line.startswith('- 当前/usr/bin/ModemManager SHA'):
  line='- 当前/usr/bin/ModemManager SHAb350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc，源949132f3…。复用190签名SDK/native增量构建，native190源码树现为191；旧源/未去RPATH程序先备份到手机k191-mm-build，主机190原源保持。ARM64源码编译告警0，系统库解析/版本与去RPATH通过，APK DB保持。190程序fbc40848…在k191-mm-deploy/ModemManager.original及主机kernel191/ModemManager.before191，发行版原件4d5a8258…仍在190。激活文件/INFO恢复；补丁仍需正式入包，包更新/旧rootfs会覆盖。'
 elif line.startswith('- 190主私人归档'):
  line='- 191主私人归档SHA843c4d47…/42文件，归档及各成员哈希、原/新程序已核对保存。190主461318d5…/322文件、USB补充e4bb35dd…及不完整副本、189完整7f80cdca…均保留。191核对Wi-Fi服务NV源manifest/蓝牙配置，重要分区/NV/校准备份未覆盖；固定BDS164/固件172/FdtBlob129及183/181回退保持。'
 result.append(line)
text='\n'.join(result)+'\n';start=text.index('1. 优先审查');end=text.index('\n导航：',start)
text=text[:start]+'''1. GPS辅助发现与完整文件注入的确定缺陷已修复，但300秒无fix/无有效CNR，16条SV事件缺省列表，接收条件与RF/平台原因尚不能区分。继续本机GPS/RF供电/时钟/固件状态核对，并验证GNSS-only GeoClue客户端及自动辅助加载；配置排除其它定位提供者，保留正常授权，不冒用Phosh或伪造坐标。
2. 191独立UTC注入ACK/status0、CID释放和close_async完成；190失败记录保持。生产UTC/位置回调257场景主机覆盖，不等于原生请求均触发。Predicted Orbits原生不支持而回退XTRA；完整50片按Part Number关联，不能简单按indication事务号归组。168小时有效期不证明跨基带重启保留，正式打包/冷启/长稳开放。
3. USB190双向IPv6不通但同boot无所列kernel故障，一次NCM gadget重绑无正向恢复证据，Windows网卡复位拒绝访问。当前Wi-Fi管理正常；继续实际USB数据/邻居链路定位，不用旧USB scope假设手机重启。曾误读磁盘表格，E盘实际约80GB可用，未删除或迁移材料。
4. 189第2轮Wi-Fi35秒未关联，后来经过第3轮PM才恢复，不能称自行恢复。BT phase5/3.2Mbps/chunk13/partial0/firstff重组1与185旧phase2前导00不同；继续修复，按边界只扫描。
5. FastRPC普通信号/freezer竞态、186共享池stop/start/reclaim−22/SSR及传感器人工运动/方向/亮暗/精度、跨boot/冷启/长稳开放。失败SCM原型ba187458…源/95c9e2b0…模块不能当修复；实际VMIDs3/5/6，勿试遍未知owner或隐藏错误。
6. 蜂窝MM仍报告sim-missing，物理卡槽/UIM状态、注册/数据/通话/SMS尚无业务验收；不要仅凭该状态断言用户未插卡。实体camera PM8008四输入/冷地址/复位/chip-enable、CCI/C-PHY和真实出图未解决，内部TPG不是实体摄像头。其它见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。
''' +text[end:]
assert len(text.encode())<=6500,len(text.encode());path.write_text(text)
path=root/'linux-port/docs/HARDWARE-STATUS.md';content=path.read_text().splitlines();assert content[2].startswith('用途：')
content[2]='用途：当前硬件验收清单。最后核对：2026-10-15，阶段191。MM四条LOC注入顺序/引用修复已部署，真实50片轨道注入、49次完成先于ACK，固件有效期0→168小时；UTC完整清理通过，随后300秒GPS仍无fix。5871.48秒同189 boot/taint0，三个DSP与SensorProxy保持；kernel183/logdump183、boot/DTB172、modules132两覆盖、Mesa149/UCM173及189三轮传感器PM范围保持。USB190未证明恢复，当前Wi-Fi管理。见[191](../../reference/kernel191/README.md)、[190](../../reference/kernel190/README.md)。完整goal active；规则见[边界](../../WORKING-BOUNDARIES.md)。'
for i,line in enumerate(content):
 if line.startswith('| GNSS定位 |'):
  content[i]='| GNSS定位 | 190能力发现+191四条LOC异步路径修复已部署，XTRA/3服务器；真实50406字节50片注入约0.801秒，49次完成先到、固件有效期0→168小时；UTC ACK/status0/释放/关闭通过，300秒303条NMEA校验通过 | 仍无有效GGA/RMC/raw/CNR，16条SV事件无列表，in-view最多13不算跟踪；真实fix、接收/RF/平台差异、GNSS-only GeoClue/自动加载、精度/冷热启/长稳待验。Predicted成功路径/生产时间与位置回调只有主机顺序覆盖，未伪造未知坐标 |'
 if line.startswith('| 蜂窝通话与数据 |'):
  content[i]='| 蜂窝通话与数据 | MPSS、QRTR/QMI、ModemManager/IPA基础已接入，本轮modem running | MM仍报告sim-missing，物理卡槽/UIM/真实SIM注册、移动数据、通话/SMS及SSR/冷启/休眠待验；该状态不等于已证明用户未插卡 |'
path.write_text('\n'.join(content)+'\n')
print('Stage191 checkpoint and hardware status updated; previous checkpoint archived verbatim; characters:',len(text))
