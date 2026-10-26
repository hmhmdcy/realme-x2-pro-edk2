from pathlib import Path
import json

here=Path(__file__).resolve().parent;repo=here.parents[1]
private=Path('/mnt/e/edk2-samurai-out/kernel208')
health=json.loads((here/'final-health-validation.json').read_text())
assert health['nmea_mask_independently_verified']==63 and health['gnss_enabled']==0 and health['taint']==0
assert json.loads((here/'evidence-export-validation.json').read_text())['all_regular_member_hashes_verified']
text='''# Realme X2 Pro 当前检查点

2026-10-15，阶段208，完整外设goal active。本轮取得原厂GNSS时钟/ADC/增益/XTRA诊断并完成临时设置恢复；仍无fix/正CNR。产品保持207状态，208没有重启、刷写或安装产品程序。[208报告](reference/kernel208/README.md)、[完整207快照](archive/NEXT-SESSION-through207-2026-10-15.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- 当前运输 `reference/kernel208/host.py`，guard `/var/lib/samurai/k208-baseline/boot-id-private.txt`，已核对仍是207第二boot。208诊断worker均终态，无待确认切换。207两轮普通重启均已完成，旧marker不得重放；k207-runtime属于第一207boot，不能作为当前身份。
- 仍部署TFTP b3bb82b9…、samurai-wifi854c9a8c…、MCFG复制程序d4c62be6…、Image183/boot204 cdd16e29…/实际DTB b9d9c2a1…/CAMSS82cbc052…，原BT185、MM191/签名APK203/helper421/init54/SSC9a1保持。本轮不改RF/供电/NV，也无BT连接配对、振动或相机帧。
- 原厂固定提交core/SystemStatus定义PQWM1和PQWP3/4/5；实机libqmi已有DEBUG=0x20000，旧SDK不代表当前能力。原mask63只读查询通过；首脚本因不支持的fix-session-state信号在GPS启动前失败，清理完整。新目录/marker的修正版临时设131135、由MM启GPS，120.29秒完成，原mask63/GPS0读回并释放CID/关闭。
- 旁路LOC客户端有ON/OFF但NMEA0；同一会话中MM GetLocation的20.35秒窗口取得147条不同NMEA，含20PQWM1、各20PQWP2至6、20GGA/4GSV，checksum0。有效GGA/RMC、正CNR、raw坐标字典仍0。旁路空流不能当作基带没有输出。
- 20PQWM1报告TimeValid1/source3（外部注入）、TimeUncNs约6.0004秒；PGA−6至−4、ADC I142至174/Q134至164、GPS AGC0.21至1.55，恢复错误字段0。它们不是RF正常验收，jammer值64至65的正常范围也未证实。PQWP3五类星座有效mask31，GPS/GLO/BDS/GAL/QZSS预测数据覆盖30/21/13/26/3颗；PQWP4接收星历均0。PQWP2可能含位置，所有原句只留私人目录。
- 2177.49秒独立健康：三个DSP running、taint/五类fault0、NV源不变、原BT185及207二进制保持，mask63/GPS0/Signalsfalse/rate30，无需再次归一化。watch累计2/2（本轮只新增1个GPS会话），辅助窗口当前168h。57份208原生文件已私人归档逐成员核对；无测试worker。

## 源码、产物与回退依据

- 本轮仅新增reference/kernel208诊断/解析/检查脚本，手机工具在/var/lib/samurai/k208-loc-tools，无产品替换需回退。负数/小数/64位/缺省不作0/校验和与截断已验证。新采集应从MM读取debug NMEA，不能仅依赖旁路LOC客户端。
- 内核 `/home/cy122/pmos-samurai-kernel136/kernel` 仍204源码，25 tracked/11 untracked未暂存，Image183/config55f1…/canonical DTB22c1…/符号16793/order770保持。205诊断早已撤回，GENI产品源码未改、旧harness首次失败尚未续完。
- 207已修复TFTP块回绕并完成1,048,603字节真实QRTR跨回绕和14次/26,580字节回归；本机原厂MCFG173文件/8,807,671字节自动复制、mdtime可读，但mcfg.tmp零字节，整体蜂窝配置未验收。PDC1平台/25软件、活动存在/无pending是207实测。
- TFTP原件/环境在手机k207-tftp-deploy，MCFG部署前helper在k207-mcfg-deploy-r2；按当前boot/PID核对后仅回退TFTP无需MPSS重启。新radio尚未APK化、旧rootfs132未整合。207的290文件归档及原厂备份保持；所有端点、原始NMEA、MCFG清单/私有归档指纹仅在E:/edk2-samurai-out。

## 续作与已知风险

下一步核对UTC误差：helper421固定注入1000ms，IDL单位已确认；是否应按chrony的abs(systemoffset)+rootdispersion+rootdelay/2及传输余量收紧，需要实测，208未改该值，不能宣称6秒不确定度就是收星根因。NTP首次启动延迟和GeoClue晚到Signals/rate仍开放，直接MM诊断本次未见晚到。不要重复同样短NMEA测试代替新变量/诊断。

真实定位/RF/LNA/时钟/天空条件、GNSS精度冷启/SSR仍待解决；不要从ADC数值推断天线正常或盲改NV/GPIO/供电。保留[realme/一加/OPPO对照](reference/kernel205/GNSS-RELATED-DEVICES.md)，他机L5/LPP配置不能直接当本机根因。

相机常态sensor图/用户态、PM8008未知PLDO输入及冷启继续；200四轮12帧IMX471只是历史开发overlay，当前boot必须重读动态phandle/GPIO。真实蜂窝注册/数据/通话/SMS、传感器精度/FastRPC共享池与SSR、SSC首次204退出、BT phase5、Wi-Fi/USB PM、完整充电与其它外设，以及可复现APK/rootfs整合均未完成。[完整硬件清单](linux-port/docs/HARDWARE-STATUS.md)。
'''
assert len(text.encode())<=6500,len(text.encode())
(repo/'NEXT-SESSION.md').write_text(text)
status=repo/'linux-port/docs/HARDWARE-STATUS.md';data=status.read_text()
start=data.index('用途：');end=data.index('\n\n',start)
data=data[:start]+'用途：当前硬件验收清单。最后核对2026-10-15，阶段208。原厂DEBUG NMEA的时钟/ADC/增益/XTRA诊断取得，临时掩码恢复；真实fix/正CNR仍0。产品保持207状态，最后三个DSP running、taint/fault0，完整goal active。[208报告](../../reference/kernel208/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+data[end:]
lines=data.splitlines()
for i,line in enumerate(lines):
    if line.startswith('| GNSS定位 |'):
        lines[i]='| GNSS定位 | 208临时DEBUG NMEA通过MM取得20组时钟/ADC/增益与XTRA诊断，接收器报告五星座辅助有效；120秒会话后mask63/GPS0恢复、独立核对通过。207原厂MCFG173文件自动复制、TFTP回绕/辅助168h保持 | 真实fix/正CNR仍0；时钟约6秒不确定度需按协议/chrony误差核对，ADC变化不证明RF/天线正常。初始化/天空条件、精度冷启/SSR、NTP启动延迟、晚到Signals/rate和完整radio APK/rootfs仍开放 |'
status.write_text('\n'.join(lines)+'\n')
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='208 diagnostics complete and restored.57 native files privately archived/verified. See rootNEXT and208README. Products unchanged; current207 secondboot; no pendingworker/reboot.',next='Finish source and publicmirror check, then continue UTC uncertainty/network bootstrap and realreceiver conditions plus all camera/cellular/sensor/BT/PM/rootfs work. Do not repeat208 worker submissions.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
(here/'finalize-source.py').write_text((here.parent/'kernel207/finalize-source.py').read_text().replace('kernel207','kernel208').replace('stage=207','stage=208'))
print(json.dumps(dict(stage=208,checkpoint_bytes=len(text.encode()),hardware_status_updated=True,no_transition_pending=True)))
