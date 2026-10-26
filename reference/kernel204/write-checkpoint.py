from pathlib import Path
import json

here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel204')
health=json.loads((here/'reboot-r2/native-health-validation.json').read_text());test=json.loads((here/'reboot-r2/geoclue-first-session-validation.json').read_text());archive=json.loads((here/'reboot-r2/archive-validation.json').read_text())
assert health['ssc_automatic_start_and_real_readiness_passed'] and not any(health['fault_counts'].values())
nextfile=repo/'NEXT-SESSION.md';old=repo/'archive/NEXT-SESSION-through203-2026-10-15.md';assert not old.exists();old.write_bytes(nextfile.read_bytes())
text=f'''# Realme X2 Pro 当前检查点

2026-10-15，阶段204，完整外设goal active。已部署蓝牙UART RX wake/sleep；首轮45.14秒RTC PM/醒后扫描通过，但phase5启动错误仍复现。第二次普通启动三个DSP/SensorProxy恢复，最后{health['uptime_seconds']:.2f}秒taint0/fault0。[204报告](reference/kernel204/README.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与实机依据

- boot204 cdd16e29…/静态DTB b9d9c2a1…，CAMSS82cbc052…四域保持；Image183/logdump183、modules132覆盖hci_uart185/fastrpc189、Mesa149/UCM173。
- UART13补GPIO46下降沿RX wake，sleep CTS/RTS下拉、TX/RX上拉；本机19781与X3参考支持此接线。当前power/wakeup enabled，原21固件/3.2Mbps/供电保持。首轮9设备→45.1438秒s2idle→13设备，success1/fail0/RTC1/错误增量0。RTC测试不证明外部BT事件唤醒。
- 首轮仍phase5/3.2Mbps/chunk13/partial0/firstff重组1，未修复；另SSC文件服务就绪退出、SLPI清理offline。未同boot重试。补观测源码9a1fd03f…记录退出码/ownership；第二boot自动真实加速度/光线readiness和三Has通过，不把偶发失败改成已修复。
- MM/openrc/udev 1.25.95_git20261005-r1、libmm-glib原r0，helper/stack0.1.0-r0，五签名APK保持；MM b350c55b…、helper42168f33…/init54b81745…不变。新boot加载inode正常，旧203(deleted)仅历史。
- 新boot helper自动空闲UTC第3次准备成功。首次180秒UID10000 GNSS-only：{test['unique_nmea']}条NMEA/{test['ggatime_distinct']}推进GGA时间，fix/正CNR/坐标事件仍0。辅助窗口0小时→自动刷新，当前{health['validity_start']}/{health['validity_hours']}小时，独立复核通过；准备3/完成3、worker1/完成1、idle。
- Power1/State−1/原因2/bearer0；GPS0/Signalsfalse/rate30，桌面定位恢复false、临时测试资源清理。三个DSP running/SensorProxy三Has true，CAMSS自动绑定，无新增相机帧；200四轮12帧RAW10仍仅历史，正常boot仍空sensor图。

[启动r2](reference/kernel204/reboot-r2/runtime-validation.json)、[健康](reference/kernel204/reboot-r2/native-health-validation.json)、[GNSS](reference/kernel204/reboot-r2/geoclue-first-session-validation.json)。历史逐字快照：[203](archive/NEXT-SESSION-through203-2026-10-15.md)、[200相机完整索引](archive/NEXT-SESSION-through200-2026-10-15.md)，相对链接按根解释。

## 源码、产物与回退依据

- 内核WSL /home/cy122/pmos-samurai-kernel136/kernel。原203源子集保持，board DTS439db943…已改/编译；部署为保持旧phandle的b9d9c2a1…静态候选。旧canonical DTB22c1f2ad…未覆盖，不能把它当boot204产物。Image bfa72dd9…/config55f1f0a3…、符号16793/顺序770、25 tracked/11 untracked未暂存保持。[源码](reference/kernel204/source-final-validation.json)
- 产品源linux-port/packages和linux-port/ssc；MM/轨道补丁/签名仓库等详见203快照。手机仓库/var/lib/samurai/packages/gnss-203，配置/etc/apk/repositories.d/50-samurai-gnss.list；仅公开key在手机。私钥仅主机/home/cy122/x2pro-linux/samurai-packages203/signing-private，勿复制或重生成。离线rootfs132未更新，Mesa等仍可能被官方包覆盖。
- 当前fresh身份手机/var/lib/samurai/k204r2-runtime/boot-id-private.txt；仅用reference/kernel204/reboot-r2/host.py的新USB peer/原严格key。kernel204主host属于首轮旧boot，203/202 host更旧。当前UID10000 Phosh实际bus在k204r2-runtime/desktop-env-private.json，勿猜/run/user/10000/bus。
- boot204主机kernel204/boot-partition-k204-bt-wake.img，cdd16e29…/100663296字节；回退boot200 5109097b…在kernel204/boot-rollback-k200-private.img，与当前CAMSS82cbc052…成对。更早boot172/旧CAMSS回退见203/200快照；fresh身份后执行，保留logdump183 e73754c7…/persist/NV。204共刷boot一次、两次受控启动，第二次无flash。
- 相机overlay5109da88…/MCLK sleep下拉，FW固定samurai/k196-front.dtbo；VIO初始RPMH unknown允许；200 GPIO12/15/29 CTL1/1/1，0390c000/0390f000/0351d000。旧boot15=0不沿用，临时phandle301已移除。PM8008 P0/Q1及Q4/5只warm证据，仅S8C输入已证；四PLDO输入未知，勿套Hotdog PM8009/BOB/master0。新boot下次操作前重读。
- 首轮468文件/末轮{archive['private_files']}文件私有归档与逐成员校验通过；NMEA/端点/身份/配对key/归档指纹仅E:/edk2-samurai-out/kernel204及reboot-r2。初次BlueZ Not Powered前置错误、第一次final-health错误假定GPS空闲窗口仍有效、UTC观察超时、SSC/BT启动失败均保留。

## 续作与已知风险

1. BT phase5下一步采集出错chunk内容及baud/flow/IBS时序；不得扩大185仅phase2 NUL过滤或盲丢0xff。RX wake/sleep已补，但外部事件唤醒、配对/连接/音频及长稳未验收，按边界只扫描。
2. SSC首次退出根因未知，第二boot恢复不是修复证明；现有观测可留存下一次退出码。FastRPC普通信号/freezer/共享池−22/SSR、传感器物理运动/方向/亮暗/精度长稳仍待验。
3. GNSS真实fix/CNR/RF/LNA/接收条件/电源/精度长稳开放；首次请求抢先/SSR、非零过期窗口仍未验收。OEM19781仅通用GNSS UART注释，勿杜撰LNA电源。可只读查PDC/MCFG时序；Hotdog蜂窝也未完成，勿停当前MM或激活外机配置。
4. 相机常态资源/用户态、四PLDO输入/双PMIC真cold、其它镜头模式/曝光色彩方向/持续帧率；蜂窝真实注册/数据/通话/SMS、Wi-Fi/USB PM及完整rootfs继续。203 USB大SCP停顿未修复；本轮PM中的传输暂时失败未触发重复试验。SIM-missing不证明物理无卡；用户无耳机勿再问，振动不新增脉冲。[硬件清单](linux-port/docs/HARDWARE-STATUS.md)

导航：[会话索引](sessions/INDEX.md)、[文档索引](DOCS-INDEX.md)。
'''
assert len(text.encode())<=6500,len(text.encode());nextfile.write_text(text,encoding='utf-8')
status=repo/'linux-port/docs/HARDWARE-STATUS.md';data=status.read_text();start=data.index('用途：');end=data.index('\n\n',start)
data=data[:start]+f"用途：当前硬件验收清单。最后核对2026-10-15，阶段204。蓝牙UART RX wake/sleep已部署，首轮45.14秒RTC PM及前后扫描通过，但phase5启动错误仍复现。首轮SSC启动失败，第二普通启动自动恢复，最后{health['uptime_seconds']:.2f}秒taint0/fault0；GNSS空窗口自动刷新与首次桌面NMEA时间通过，仍无fix/正CNR。完整goal active。[204报告](../../reference/kernel204/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。"+data[end:]
data=data.replace('203同boot三个DSP running/SensorProxy三Has true','204第二boot自动真实readiness及三个DSP/SensorProxy三Has通过，首轮文件服务就绪失败清理offline仍保留')
data=data.replace('202两次重启CAMSS四域自动加载绑定，203同boot保持，无新增帧','204第二boot CAMSS四域自动加载绑定，无新增帧')
data=data.replace('| 蓝牙 | 200新boot', '| 蓝牙 | 204 RX wake/sleep已部署；首轮前9/45.14秒RTC PM后13、错误增量0，第二boot启动重组0，外部BT事件唤醒未验；首轮phase5仍1。200新boot')
data=data.replace('| GNSS定位 | 202空闲UTC', '| GNSS定位 | 204第二boot首次182秒188条NMEA/176推进时间，自动1下载/1注入从0到168小时并独立复核，仍无fix/正CNR。202空闲UTC')
data=data.replace('APK/新rootfs整合待做','helper/MM签名APK已落地；新完整rootfs待做')
status.write_text(data,encoding='utf-8')
plan=dict(stage=204,next_stage=205,goal_still_active=True,current_boot_guard='/var/lib/samurai/k204r2-runtime/boot-id-private.txt',transport='reference/kernel204/reboot-r2/host.py; fresh USB scoped peer strict original key',old_transports='kernel204 main host is first204boot;203/202 older',
 boot='204:cdd16e29f3639dd79fe7c1a98ac3a5fcb2827d701d2291af93a4da0884476082; DTB b9d9c2a1; CAMSS82cbc052; Image/logdump183; modules132+185/189',rollback='kernel204/boot-rollback-k200-private.img 5109097b, sameCAMSS82cbc052; older172 pairing in203snapshot',
 helper='42168f33/init54; prep3/completion3,worker1/completion1 idle after first packaged desktop session; GPS0 Signalsfalse rate30 Power1; MMb350 loaded current normal inode',
 ssc='9a1fd03f adds readiness exit/status observation only; firstcycle failed and stopped; second automatic real accel/light readiness and3Has running; failure rootcause unresolved',
 next=['Investigate phase5 3.2Mbps/chunk13/firstff with bounded full-chunk RX and baud/flow/IBS evidence; do not discard unknownff data or assume RX wake fixed it.',
 'Leave SSC exit observation for recurrence; verify source startup mismatch vs daemon actual exit status when evidence exists; never retry sharedpool SLPI sameboot blindly.',
 'Camera persistent sensor graph/userspace and unknownPLDO inputs/cold;GNSS actualRF/fix;cellular PDC read-only and real business;FastRPC ordinarysignal/sharedpool/SSR;WiFi/USBPM;newrootfs remain.'],
 current_health=health,private_archives=['first-boot-evidence-private.tar.gz:468files','reboot-r2/final-evidence-private.tar.gz:'+str(archive['private_files'])+'files'],retained_boundaries='WORKING-BOUNDARIES; noBTpair/connect;nohaptics;noheadset available')
(private/'next205-plan-private.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps(dict(stage=204,checkpoint_bytes=len(text.encode()),hardware_status_updated=True,private_next205_plan_saved=True)))
