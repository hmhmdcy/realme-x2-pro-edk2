from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel221')
assert json.loads((here/'final-evidence-validation.json').read_text())['archive_and_all_member_hashes_verified']
health=json.loads((here/'final-health-validation.json').read_text());assert health['taint']==0
old=(repo/'NEXT-SESSION.md').read_text();archive=repo/'archive/NEXT-SESSION-through220-2026-10-16.md';assert not archive.exists();archive.write_text(old)
next_text='''# Realme X2 Pro 当前检查点

2026-10-16，221：同boot219/e49与完整libcamera r7/config-r2；新增只读LOC星座/黑名单诊断，GPS强制启用、四星座内部启用，四个已返回黑名单为0。真实fix/CNR未解决。全外设goal active。[221记录](reference/kernel221/README.md)、[220元数据修复](reference/kernel220/README.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- 运输reference/kernel221/host.py，新USB邻居/原严格公钥；guard /var/lib/samurai/k221-baseline/boot-id-private.txt，与219-runtime/220-baseline同boot。218及219-baseline/before-reboot旧身份不可授权新切换。无活任务/待恢复切换；219marker closed、220包事务verified。BT只扫描、不新增振动。
- boot219 156f0370…/DTB a214fd6b…，前摄200/400/748.8MHz；Image183 bfa72dd9…/logdump183 e73754c7…保持，NV保持。当前IMX471 e49dab26…，CCI f9c9272a…/PM8008 d1ff82c0…/CAMSS82cbc052…，772ko/786文件。TFTP207/MCFG、MM191/GNSS/SSC、Wi-Fi及BT185指纹见219，无本轮改动。
- 前摄CCI1 master1/0x10、MCLK2 19.2MHz、4lane/CSIPHY2/独立TITAN_TOP。默认1928×1088/2304×1728，完整4608×3456需模块+用户态两个实验开关，当前N。COMPOSE已删；真实CROP/FOV/CFA仍开放。
- libcamera/IPA/tools/gstreamer/v4l2为99990.7.2-r7，config/stack0.1.0-r2；944包/937无关记录保持、49payload核对。CPU/system heap，配置与r1逐字相同；通用堆root/video0660+uaccess、DSP池root0600。WP为手动进程，仅重载WP需现取argv/env/UID10000，保留桌面/PipeWire身份。
- 219真实4MP/实验16MP RAW与CPU RGB各六帧，暗RAW噪声约0.47/0.60、帧变化35%/51%；DMA同步且不存图。r5第三个4MP RGB缓冲分配失败，r6起system heap四缓冲通过。全模式TPG仍普通Bayer，不能证明Quad真实颜色；关灯后暗RGB不能单判bug。
- 时序已修：旧LLP5120，三模式像素率387200000/326400000/578133333，PLL不改；120帧RAW约57.82018/30.00030/60.03122/30.01381fps符合控件，不证明CPU RGB30fps。
- 220修复IPA init缓存4MP时序：2MP1290行从错误10117µs改报17057µs，计算17057.85µs。0013每次configure传sensorInfo；候选/隔离代理/已装共288帧，差<1µs整数化。未验物理曝光精度/延迟；标准手动曝光API仍未接入。13包/34ELF/5IPA/Qt/Python及默认Gst六帧通过。
- 221只读C工具/SDK源固定，原生k221-loc-readonly-r3，源cef74ac6…/程序d7fb4c24…。四GET：0x4b standalone；0xbf GPS0强制、GLO/BDS/QZSS/GAL1内部启用；0xb7这四黑名单0；0xe1被ACK error57/WmsInvalidMessageId拒绝。缺省NavIC/GPS黑名单等不能当0，多频查询拒绝不等于硬件不支持。ACK/ind先后与完整CID释放/关闭核对，两轮一致；第二版r2原结果保留。
- 当前engine lock mt/NMEA63、Power1/DMS shutting-down、MM failed/原因2、SIM对象无、bearer0。两UIM no-atr、两槽absent/active，与191相同，不证明物理未插卡。191/201 online仍无CNR，本轮未重复电源切换。
- 最终k221-final-health：同boot/49相机payload/e49保持，cam/CCI/CAMSS休眠，两前摄电源关闭/用户0、参数N；GPS0/Signalsfalse/rate30、watch空闲/无新增worker、chrony Normal，三DSP running，BT关无连接，taint/五fault0，NV源保持。无本轮拍摄/引擎启动/重启/刷写。

## 源码、产物与回退依据

- kernel /home/cy122/pmos-samurai-kernel136/kernel canonical仍216源cc756279…/对象1388a070…/旧DTB22c1…，原25 tracked/11 untracked；不可把旧DTB当部署树。实际219私人timing-source/imx471.c61931497…，e49模块/a214DTB，四补丁链已重放核对。
- 模块回退设备k219-timing-baseline/imx471-original.ko d82c941d…及k219-timing-driver-test-r2/before-tree；更早216在k219-baseline。现取身份/空闲，正常解绑/卸载/恢复/depmod/加载/策略恢复，不强卸。boot回退私人211/boot-partition-k211-sensor-domain.img c3bf043f…，与模块分别核对。
- SDK /home/cy122/x2pro-linux/libcamera214-root，原/work/libcamera的2254文件/链接已恢复；r7完整源/对象/work/libcamera220-built，配方/work/libcamera220与/work/samurai-camera-config220，13包/packages220、/packages-config220及私人220/camera-forward-repo。QA前缀libcamera220-qa-prefix/chroot/candidate220，无活构建/待恢复快照。
- canonical配方/配置/源码锁/部署锁为r7/r2；0013 d6aa409f…、前12补丁/tuning/YAML保留。原IPA214与APK203私钥复用，不生成/上传；未证明二次构建逐字相同，完整kernel/rootfs整合继续。
- 220事务verified，原944包DB/world/repo/config保留；实际r6/r1回退七包在设备k219-r6-package-candidates/forward及私人219/camera-forward-repo，验签/payload/降级模拟通过，未执行完整回退往返。更早r5/r4分开保存。
- 221原生37成员私人归档逐一核对；220另146、219另512保持。新工具仅诊断，不是产品修复。初始包CLI断言、GI无Qmi.Message、SDK头弃用声明编译失败均记录；勿重放已终态脚本。USB严格邻居/原密钥/64KiB是工作绕过，截断根因未修。capsule私人kernel221/current-work-private.json；完整前交接archive/NEXT-SESSION-through220-2026-10-16.md。

## 续作与已知风险

用户关灯、室内窗边；不闪光/外部照明、不存场景。接续前摄标准手动曝光/增益与AE开关，保留r7模式信息；实际曝光/延迟、真实CFA/几何/颜色/方向/标定/GUI及RGB性能继续。后置GW1/3M5/IMX319/人像未接入，未知PLDO输入不猜；GPU ISP211 CMA/黑帧/unmap349 WARN/taint512开放，149 CCU修复保持。

GNSS无真实fix/正CNR、无遮挡户外/Android基线；星座启用不证明RF正常，继续OEM启动/RF/LNA/时钟依据。[相关机型](reference/kernel205/GNSS-RELATED-DEVICES.md)。209小UTC误差未改善约6秒报告，勿重做；208 ADC不证明RF。207 MCFG173文件/8807671B RAM复制、mdtime/PDC活动无pending通过，mcfg.tmp0B；真实SIM/注册/数据/通话/SMS/UIM开放，外发需明确目标。

BT phase5、传感器FastRPC reclaim/SSR/首启失败、Wi-Fi/USB PM、音频长稳/耳机（暂无）、充电保护闭环、指纹/NFC及旧rootfs132整合均按[硬件清单](linux-port/docs/HARDWARE-STATUS.md)继续。不要因局部验证完成/暂停全外设goal。
'''
assert len(next_text.encode())<=6500,len(next_text.encode());(repo/'NEXT-SESSION.md').write_text(next_text)
status=repo/'linux-port/docs/HARDWARE-STATUS.md';text=status.read_text();start=text.index('用途：');end=text.index('\n\n',start)
text=text[:start]+'用途：当前硬件验收清单。最后核对2026-10-16，阶段221。同boot219/e49与完整libcamera r7/config-r2保持；只读星座/黑名单查询缩小GNSS排查范围，真实定位未解决。220曝光元数据修复和288帧验证保持，全外设goal active。[221报告](../../reference/kernel221/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+text[end:]
lines=text.splitlines()
for i,line in enumerate(lines):
 if line.startswith('| GNSS定位 |'):lines[i]='| GNSS定位 | 221只读LOC：GPS强制启用、GLO/BDS/QZSS/GAL内部启用；四个已返回黑名单0，mt锁/standalone/NMEA63。GET多频被error57拒绝，不能当硬件无支持；两轮ACK/ind及CID释放/关闭通过。UTC/XTRA服务空闲、chrony正常 | 真实fix/正CNR仍未解决，室内窗边且无无遮挡户外/Android基线；星座启用不证明RF正常，未返回黑名单字段不能当0。209小UTC误差无改善结果保持；RF/LNA/时钟/OEM初始化、冷启/SSR、完整radio APK/rootfs开放 |'
 if line.startswith('| 蜂窝通话与数据 |'):lines[i]=line.replace('历史no-atr/slot absent不证明物理未插卡','221再次只读得到两槽no-atr/absent/active，与191相同，不证明物理未插卡')
status.write_text('\n'.join(lines)+'\n')
related=repo/'reference/kernel205/GNSS-RELATED-DEVICES.md';text=related.read_text();text+='\n221按[高通公开LOC实现](https://github.com/qualcomm-linux/location-apis-qcom/tree/a581b6c9ee15e3fdbb0e15f43cd37b97616b0948)补齐独立只读查询：GPS强制启用、四星座内部启用，四个返回的黑名单掩码0。新多频GET被当前接口拒绝，不等于硬件不支持；未返回字段不当0。它缩小软件禁用排查范围，没有取得真实fix/CNR，也不替代本机RF/天空基线。[221原生证据](../kernel221/README.md)。\n';related.write_text(text)
state=json.loads((private/'current-work-private.json').read_text());state.update(state='221 read-only LOC constellation/blacklist queries and UIM recheck complete;37 native archive members verified; deployed boot219/e49/r7/r2 unchanged',transition_pending=False,active_session=None,next='Connect standard libcamera exposure/gain and AE controls while retaining r7 timing and dark-scene numerical validation. Continue GNSS OEM/RF source work with constellation-disable hypothesis narrowed, no repeat of209 time test; all original peripheral goals active.')
(private/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=221,next_session_bytes=len(next_text.encode()),full_goal_active=True,phone_configuration_unchanged=True)))
