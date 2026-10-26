from pathlib import Path
import json

here=Path(__file__).resolve().parent
repo=here.parents[1]
health=json.loads((here/'reboot-r2/final-health-validation.json').read_text())
archive=json.loads((here/'reboot-r2/evidence-export-validation.json').read_text())
assert health['same_second207_boot_verified'] and health['taint']==0 and archive['all_regular_member_hashes_verified']
text='''# Realme X2 Pro 当前检查点

2026-10-15，阶段207，完整外设goal active。TFTP块号回绕与缺失的本机原厂MCFG目录已修复并部署；第二次普通启动自动复制173份MCFG通过，但GNSS仍无真实fix/正CNR。本轮两次普通重启、没有刷写。[207报告](reference/kernel207/README.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- 当前运输 `reference/kernel207/reboot-r2/host.py`，guard `/var/lib/samurai/k207r2-runtime/boot-id-private.txt`。两次207切换及新boot身份均已确认，没有待确认重启/测试worker；不得重放首轮或第二轮marker。旧k207-baseline属于205第二boot，k207-runtime属于207第一boot，均不是当前身份。
- TFTP b3bb82b9…、samurai-wifi 854c9a8c…、新增samurai-modem-configs d4c62be6…；32MiB私有tmpfs工作文件、单文件8MiB保持。内核仍Image183/boot204 cdd16e29…/实际DTB b9d9c2a1…/CAMSS82cbc052…，原hci_uart185、MM191/签名APK203/helper421/init54与SSC9a1保持。
- 独立真实QRTR复现旧writer绝对块65539 ACK错误、旧reader第65537块错读。新绝对计数完成1,048,603字节写入/逐字读回、两次回绕；14次/26,580字节含重复DATA/ACK等在独立及正式实例通过。测试实例/挂载/正式缓存测试文件已清理。固定十份源码缓存重建Werror0告警，完整patch/source-lock及构建入口在linux-port/radio。
- 第一207boot暴露只读modem_pr/mcfg目录缺失；只读本机modem分区实际173文件/8,807,671字节。新程序复制到私有RAM并逐项核对，正式QRTR读回mdtime12字节与源相同。第二207boot自动复制全部173文件、hash匹配；125.78秒实际modem已请求/打开mdtime11次、该目录打开错误0。mcfg.tmp仍0字节，不能据此声称配置初始化或蜂窝完成。PDC仍有活动平台/软件、无pending，独立列表1平台/25软件且活动元数据成功。
- 第二207boot首次UTC等待超时，Wi-Fi global连接但chrony未同步；刷新现有NTP来源refresh/online/burst后Normal，GNSS服务自动UTC准备19/19。没有手动设置时钟或注入UTC，但整条时钟bootstrap不能算全自动通过。没有为观察失败重复重启。
- 同boot首次GNSS-only GeoClue运行181.37秒：187NMEA/174推进时间/10GSV、checksum0；自动1下载/1注入建立当前168h窗口。有效GGA/RMC/raw、正CNR、位置事件仍0。测试配置/身份移除，GPS0；首次最终检查联合空闲断言失败保留，独立观察又见晚到Signals=true/rate0，保存后恢复false/30，竞态未修复。
- 673.02秒最终检查三个DSP running、taint/五类fault0，NV源校验保持，辅助窗口独立复核有效，Power1/State−1/原因2。没有新的BT配对/连接、振动或摄像头帧。两次207启动与测试290份文件私人归档并逐成员核对。

## 源码、产物与回退依据

- 内核 `/home/cy122/pmos-samurai-kernel136/kernel` 仍204源状态，25 tracked/11 untracked未暂存，Image183/config55f1…/旧canonical DTB22c1…/符号16793/order770保持；此次仅用户态修复。源锁与脚本语法已核对。205诊断模块/helper/BlueZ早已恢复；GENI产品源码未改，原失败harness未续完。
- TFTP原206程序及服务环境在手机 `/var/lib/samurai/k207-tftp-deploy/`，MCFG部署前helper在 `k207-mcfg-deploy-r2/`。回退前按当前boot/PID/文件核对；仅回退TFTP无需重启MPSS。原厂MCFG与manifest只留私人目录，不能发布或替换为他机NV。新TFTP/helper尚未形成APK，旧离线rootfs132未整合。
- 原始NMEA/QMI、MCFG文件清单、端点/身份和归档指纹在E:/edk2-samurai-out；公开报告只给验收计数。[206完整检查点](archive/NEXT-SESSION-through206-2026-10-15.md)保留历史原文；205/206归档也保持。[相关机型对照](reference/kernel205/GNSS-RELATED-DEVICES.md)保存realme/一加/OPPO具体实现与适用范围。

## 续作与已知风险

不要再用相同的短NMEA会话代替根因工作。补齐MCFG后仍无正CNR，下一步核对原厂定位初始化、可用的接收器/AGC/干扰/时钟诊断及真实天空条件；先确认公开协议与本机能力，不能盲改LNA GPIO/供电或移植他机NV。当前活动MCFG存在，LPP配置2/3或GT2 Pro的L5开关尚无本机因果证据。首次时钟延迟、晚到Signals/rate、TFTP长期生命周期与完整协议、GNSS冷启/精度/SSR仍开放。

摄像头常态sensor图/用户态、PM8008未知PLDO输入及冷启仍开放；200四轮12帧IMX471只是历史开发overlay，当前boot须重新读取动态phandle/GPIO。真实蜂窝SIM注册/数据/通话/SMS、传感器物理精度/FastRPC共享池与SSR、SSC首次204退出、BT phase5、Wi-Fi/USB PM、完整充电及其它外设继续属于完整目标。不能用本轮文件服务成功缩小目标。[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。
'''
assert len(text.encode())<=6500,len(text.encode())
(repo/'NEXT-SESSION.md').write_text(text)
status=repo/'linux-port/docs/HARDWARE-STATUS.md'
data=status.read_text()
start=data.index('用途：');end=data.index('\n\n',start)
data=data[:start]+'用途：当前硬件验收清单。最后核对2026-10-15，阶段207。TFTP块号回绕与本机原厂MCFG目录已补齐，第二普通启动173文件自动复制通过；187条NMEA仍无fix/正CNR。最后三个DSP running、taint/fault0；完整goal active。[207报告](../../reference/kernel207/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+data[end:]
lines=data.splitlines()
for index,line in enumerate(lines):
    if line.startswith('| GNSS定位 |'):
        lines[index]='| GNSS定位 | 207第二boot首次GNSS-only181.37秒，187NMEA/174推进时间/10GSV，自动1下载/1注入当前168h；TFTP回绕真实QRTR通过，本机原厂MCFG173文件自动复制且modem可读mdtime；MM/helper签名APK203保持 | fix/正CNR/位置事件仍0；原厂初始化/RF/LNA/时钟与天空条件、精度冷启/SSR、晚到Signals/rate、NTP启动延迟、完整rootfs和TFTP包整合仍开放，不能把文件服务修复算定位成功 |'
    elif line.startswith('| 蜂窝通话与数据 |'):
        lines[index]='| 蜂窝通话与数据 | MPSS、QRTR/QMI、ModemManager/IPA基础接入；207两次普通启动modem running，原厂MCFG目录自动复制且mdtime可读；PDC活动平台/软件存在、无pending、1平台/25软件列表通过；当前Power1、failed/原因2、bearer0 | mcgf.tmp仍零字节，整体配置初始化与真实SIM注册/数据/通话/SMS/UIM仍待验；历史no-atr/slot absent不证明物理未插卡；电源策略/SSR/冷启/休眠开放 |'.replace('mcgf.tmp','mcfg.tmp')
status.write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(stage=207,checkpoint_bytes=len(text.encode()),hardware_status_updated=True,current_guard_correct=True,no_transition_pending=True)))
