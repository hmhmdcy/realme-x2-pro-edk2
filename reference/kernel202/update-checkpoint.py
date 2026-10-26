from pathlib import Path

root=Path(__file__).resolve().parents[2]
current=root/'NEXT-SESSION.md';archive=root/'archive/NEXT-SESSION-through201-2026-10-15.md'
assert current.read_bytes()==archive.read_bytes()
text='''# Realme X2 Pro 当前检查点

最后核对：2026-10-15，阶段202，完整外设goal active。两次普通重启、无刷写；修复已复现的GPS首次会话NMEA时间为0，并实机完成空辅助窗口自动刷新。仍无fix/正CNR。最终第二轮启动504.96秒，taint0/所列fault0。见[边界](WORKING-BOUNDARIES.md)、[202报告](reference/kernel202/README.md)。

## 当前部署与实机依据

| 项目 | 最后核对 |
| --- | --- |
| 基础组合 | boot200/静态DT2e2f8e64…/CAMSS82cbc052…；Image183/logdump183、modules132覆盖hci_uart185/fastrpc189、Mesa149/UCM173/MM191保持 |
| GPS服务 | helper42168f33…/init54b81745…，OpenRC default自动启动；每MM owner在GPS空闲且chrony同步时准备一次UTC；数据仍仅GPS active刷新，无Setup/Start或电源操作 |
| 首次会话 | 旧服务新启动首182秒只有4条NMEA/时间0，第二次91条/88时间；修订后再重启首次182.36秒185条/176时间、GSV6。均UID10000 GNSS-only，未手工补时；所有fix/CNR/位置事件仍0 |
| 自动数据 | 新启动原窗口315964800/0小时，自动3次下载尝试/1次注入后1792047600/168小时，即10-15 07至10-22 07 UTC；最终独立查询仍有效 |
| 当前空闲 | MM Power1、State−1/原因2、bearer0；GPS0/Signalsfalse/刷新30，桌面定位恢复原false，policy/DesktopId/测试程序移除；helper准备3次/完成3次、数据worker1/完成1，idle |
| 整机 | ADSP/SLPI/modem running、SensorProxy三Has true；504.96秒taint0，WARNING/Oops/GPU/SLPI fatal/BT重组0；分区/NV/784模块校验一致；CAMSS两轮自动加载绑定 |
| 相机200证据 | 静态四域后四轮12帧IMX471 RAW10、自身MMCX384→0/原频率；最终三脚/PMIC恢复；临时sensor/CCI/PMIC/VIO资源已撤销，正常启动仍空sensor图 |

依据：[首次会话](reference/kernel202/geoclue-first-session-validation.json)、[启动重试](reference/kernel202/clock-startup-retry-validation.json)、[健康](reference/kernel202/native-health-validation.json)。历史逐字快照：[201](archive/NEXT-SESSION-through201-2026-10-15.md)、[200完整相机索引](archive/NEXT-SESSION-through200-2026-10-15.md)，相对链接按根解释。

## 源码、产物与回退依据

- WSL /home/cy122/pmos-samurai-kernel136/kernel，200所有源保持，25 tracked改动/11 untracked未暂存。Image183 bfa72dd9…、canonicalDTB22c1f2ad…/config55f1f0a3…、符号16793行/顺序770保持。[收据](reference/kernel202/source-final-validation.json)
- 产品源reference/kernel202/samurai-gnss-assist.py/initd，安装42168f33…/54b81745…。时钟未同步10秒重试，实际2次未同步后第3次成功；早期观察超时保留，服务未重启。有效数据跳过，空/无效数据TLS下载/标准MM注入/读回，活动每小时复查、其它普通错600秒退避。
- 空闲只准备UTC、不下载/启GPS/改电源；每MM owner一次。定位抢先到达记录竞态、不重启应用，旧owner晚结果不污染新owner。37核心检查+6生产watch场景/6退避检查通过；模拟停机/owner变化不能替代原生SSR或活跃worker中停机。
- 空窗口自动刷新实机通过；201旧e905注入Core.Aborted/未造出非零过期窗口保留，不强清校准。下载前两次失败原因未记录。
- 两轮均fresh身份、外设停妥/冻结后单次Linux→bootloader，再fresh fastboot身份/product核对后单次reboot，无flash。EUD断线的确认/传输异常未触发重发；首轮私有路径错误在reboot发送前，修正后重核，日志保留。
- 首轮晚查Signals1/rate0，原因未证，空闲归一false/30。末轮初次收尾未过、后续复核通过，未终止GeoClue；配置逐字保持、定位开关恢复false。
- MM191 b350c55b…保持，202无电源/reset操作；两次重启均Power1。首轮NM WWAN软/硬允许true；源码LOW映射low-power，OFF可对应offline/shutting-down，202未查询实际DMS模式或测试LOW。201 Power3/online是旧boot证据，不沿用为当前。
- boot200主机kernel200/boot-partition-k200-mmcx.img，5109097b…/100663296字节；四域DT2e2f8e64…/CAMSS82cbc052…配套。回退boot172 77e1a272…在kernel200/boot-rollback-k172-private.img，旧CAMSS e9b73f4c…在手机k200-baseline/k200-deploy及归档。fresh身份后旧boot/模块配套，保留logdump183 e73754c7…、persist/NV。
- 相机sensor-only overlay5109da88…/MCLK sleep pull-down，FW固定samurai/k196-front.dtbo；VIO允许RPMH初始unknown。200新bootGPIO12/15/29 CTL1/1/1，地址0x0390c000/0x0390f000/0x0351d000，旧boot15=0不得沿用；临时phandle301已移除，下次重读。
- PM8008 P0/Q1、Q4/5与8无响应仅warm证据；PLDO四输入未知，仅S8C已证，勿套hotdog PM8009/BOB/pop-up/master0布线。完整源码/hash/引脚与12帧清理细节在200快照。202未新增相机帧或BT扫描。
- 当前boot身份手机/var/lib/samurai/k202r2-runtime/boot-id-private.txt。仅用reference/kernel202/reboot-r2/host.py的新USB peer/原严格公钥；kernel202主host属于上一启动。Phosh bus已从当前UID10000实际进程重取，勿猜/run/user/10000/bus。
- 首轮110文件/末轮108文件归档及逐成员核对通过；NMEA/配置/端点/身份/归档指纹只在E:/edk2-samurai-out/kernel202及reboot-r2。200 RAW/历史备份保持私人；APK更新仍可能覆盖MM/Mesa等本地修复，旧rootfs132不含新服务。

## 续作与已知风险

1. 真实GNSS fix/CNR/RF/LNA/接收条件/电源/精度长稳仍开放；首次请求抢先及SSR待验。普通重启时间通过不等于断电冷启验收。OEM19781仅通用GNSS UART注释，未改UART/GPIO或杜撰LNA电源。
2. 正式整合helper/MM补丁APK和新rootfs；已找到/home/cy122/pmos-samurai-rootfs01/pmaports，但device目录未见自有samurai包。先检查实际构建链，当前服务是本地安装。
3. 相机板级持久资源/用户态、PLDO输入/双PMIC真正cold、其它镜头模式/曝光色彩方向/持续帧率；不能把12帧当日用完成。
4. 蜂窝真实SIM注册/数据/通话/SMS、BT phase5历史重组、Wi-Fi/USB PM、FastRPC普通信号/freezer/共享池−22/SSR、传感器物理精度与长稳继续。SIM-missing/no-atr不证明物理未插卡；用户无耳机，勿再要求。BT只扫描、振动不新增脉冲。其余见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。

导航：[会话索引](sessions/INDEX.md)、[文档索引](DOCS-INDEX.md)。
'''
encoded=text.encode();assert len(encoded)<=6500,len(encoded)
current.write_bytes(encoded)
status=root/'linux-port/docs/HARDWARE-STATUS.md';lines=status.read_text().splitlines()
for index,line in enumerate(lines):
    if line.startswith('用途：当前硬件验收清单。'):
        lines[index]='用途：当前硬件验收清单。最后核对：2026-10-15，阶段202。两次普通重启无刷写；GPS空闲自动UTC准备修复首次会话时间0，首次182秒185条NMEA/176时间；空辅助窗口全自动更新与独立读回通过，仍无fix/正CNR。最终第二轮504.96秒taint0/所列fault0，三个DSP及SensorProxy三Has正常，Power1/GPS0。完整goal active。[202报告](../../reference/kernel202/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'
    elif line.startswith('| 摄像头 |'):
        lines[index]=line.replace('| 摄像头 | 200','| 摄像头 | 202两次重启CAMSS四域自动加载绑定，无新增帧；200',1)
    elif line.startswith('| 其它传感器 |'):
        lines[index]=line.replace('| 其它传感器 | 200','| 其它传感器 | 202第二次启动三个DSP running/SensorProxy三Has true；200',1)
    elif line.startswith('| 蜂窝通话与数据 |'):
        lines[index]='| 蜂窝通话与数据 | MPSS、QRTR/QMI、ModemManager/IPA基础接入，202两次重启modem running；当前MM Power1、failed/原因2、bearer0，202无电源/reset操作 | 201 Power3/online属于旧boot；两卡位历史no-atr/slot absent，当前仍sim-missing，不证明物理未插卡；实际SIM注册/数据/通话/SMS、UIM、电源策略/SSR/断电冷启/休眠仍待验 |'
    elif line.startswith('| GNSS定位 |'):
        lines[index]='| GNSS定位 | 202空闲UTC准备后再重启，首次182秒185条NMEA/176推进时间，6条GSV；真实UID10000 GNSS-only GeoClue启停通过；服务自动把0小时窗口下载/注入/读回为当前168小时，最终独立复核，保持Power1 | 仍无有效fix/正CNR/位置事件；RF/LNA/真实接收条件/电源策略、首次请求抢先/SSR、断电冷启/精度长稳待验；非零过期窗口原生场景未造出，201受控旧注入Core.Aborted保留；APK/新rootfs整合待做 |'
status.write_text('\n'.join(lines)+'\n')
print('Updated stage202 checkpoint, bytes=%d, and full hardware scope.'%len(encoded))
