from pathlib import Path
import json
here = Path(__file__).resolve().parent
repo = here.parents[1]
out = Path('/mnt/e/edk2-samurai-out/kernel206')
health = json.loads((here / 'final-health-validation.json').read_text())
assert health['same205_r2_boot_verified'] and not health['rebooted'] and health['taint'] == 0
assert json.loads((here / 'evidence-export-validation.json').read_text())['exports']['k206']['all_regular_member_hashes_verified']
archive = repo / 'archive/NEXT-SESSION-through205-2026-10-15.md'
assert not archive.exists()
archive.write_bytes((repo / 'NEXT-SESSION.md').read_bytes())
text = '''# Realme X2 Pro 当前检查点

2026-10-15，阶段206，完整外设goal active。已修复并部署modem工作文件的RAM TFTP支持；GNSS仍无真实fix/正CNR。206没有重启或刷写，当前仍是205第二次启动。[206报告](reference/kernel206/README.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- 当前运输 `reference/kernel206/host.py`，沿用新核对的严格key USB；guard `/var/lib/samurai/k205r2-runtime/boot-id-private.txt`。没有待确认切换或重启请求；不能套用204/205第一次启动身份。
- TFTP已替换为d0906a5a…，`samurai-wifi`为ffb65d31…，新增/run/samurai-wifi/tftp-rw独立32MiB tmpfs、单文件8MiB。RMTFS和MM未重启，modem未SSR，NV源校验保持。当前真实modem的mcfg.tmp初始请求尚未重放，需正常新启动验收。
- 旧服务确实拒绝/readwrite/mcfg.tmp读写；PDC已有活动平台/软件配置，无pending，列表1平台/25软件、活动项均在。qmicli软件列表InvalidQosId失败保留，独立GI活动配置与元数据查询通过；不能推断完全缺MCFG或物理SIM状态。
- 独立QRTR实例206和正式实例0各完成13次事务、20,435字节逐字核对，含窗口/整块/范围/无选项/seek/截断/空文件/固件写拒绝。原服务拒绝相同测试。测试实例终止、挂载撤销、正式缓存中的测试文件移除。10个固定来源全新下载构建与实机程序字节完全相同，Werror0告警。通用协议的16位块回绕/异常重传等仍需补测。
- 205临时hci_uart诊断、蓝牙helper和BlueZ策略全部恢复；默认/loaded为185 f6c5ed35…，784文件原manifest核对通过、keys保持。主机hci_qca回645ded49…和原未剥离模块；GENI产品源码未改，205 C harness缺TIOCM_LOOP的首次失败仍未续完，不是已证明根因。
- 206同boot首次UID10000 GNSS-only会话182.35秒：188条NMEA/176推进时间/9GSV，checksum0；自动1下载/1注入到当前168h，独立复核仍有效，fix/正CNR/坐标事件0。会话/测试资源清理后又见晚到Signals=true/rate0，保存现场后恢复false/30；原因未解决。
- 2590.67秒[最终健康](reference/kernel206/final-health-validation.json)：三个DSP running、taint/五类fault0，GPS0，Power1/State−1/原因2。MM191 b350/签名APK203/helper421/init54、SSC9a1诊断保持。没有新的相机帧、蓝牙连接/配对或振动操作。当前无测试worker。

## 源码、产物与回退依据

- 新产品源码与构建：`linux-port/radio/`。手机原TFTP/helper和服务环境在 `/var/lib/samurai/k206-tftp-deploy/`；回退前用当前身份和PID核对，只替换TFTP/helper并按保存环境重启TFTP即可。TFTP新服务尚未形成APK；离线rootfs132未更新。
- 内核 `/home/cy122/pmos-samurai-kernel136/kernel` 源码恢复到204状态，25 tracked/11 untracked未暂存，Image183/config55f1…/符号16793/order770保持。boot204 cdd16e29…/实际DTB b9d9c2a1…/CAMSS82cbc052…，旧canonical DTB22c1…未覆盖。此次只构建用户态，无内核刷写。
- 205的259份及206的100份原生文件已私人归档、逐成员核对。原始NMEA/QMI、端点/身份/配置及归档指纹只在E:/edk2-samurai-out。205诊断与失败全部保留。旧[205检查点](archive/NEXT-SESSION-through205-2026-10-15.md)、[204完整快照](archive/NEXT-SESSION-through204-2026-10-15.md)保留原文，旧部署不替代本页。
- GNSS[相关机型对照](reference/kernel205/GNSS-RELATED-DEVICES.md)：一加6固件/运营商报告可借鉴，同平台7T Pro仍Partial；L5项目仅GT2 Pro测试，未执行或改NV。本机社区Android配置与一加39项仅LPP2/3不同，不能直接作为RF根因。

## 续作与已知风险

先补TFTP协议边界，再用更新后的helper/程序/原185模块manifest准备一次普通新启动，核对真实mcfg.tmp写入/读回、PDC状态、UTC/辅助刷新与GNSS接收。切换前按当前状态重新采集、quiesce和归档；206尚未发任何重启，不需重刷boot。实际fix/CNR、原厂初始化/RF/LNA/时钟、户外接收/精度/冷启仍开放。

摄像头正常sensor图/用户态、未知PLDO输入与冷启仍开放；200四轮12帧IMX471仅历史开发overlay，新的boot须重读动态phandle/GPIO。蜂窝真实SIM注册/数据/通话/SMS、传感器物理精度/FastRPC共享池与SSR、SSC首次204退出根因、BT phase5启动错误、Wi-Fi/USB PM、完整充电与其它外设继续推进。不要用当前局部成功缩小完整目标。详见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。
'''
assert len(text.encode()) <= 6500, len(text.encode())
(repo / 'NEXT-SESSION.md').write_text(text, encoding='utf-8')
status = repo / 'linux-port/docs/HARDWARE-STATUS.md'
saved = repo / 'archive/HARDWARE-STATUS-through204-2026-10-15.md'
assert not saved.exists(); saved.write_bytes(status.read_bytes())
data = status.read_text()
start = data.index('用途：'); end = data.index('\n\n', start)
data = data[:start] + '用途：当前硬件验收清单。最后核对2026-10-15，阶段206。modem RAM工作文件TFTP已部署并通过真实QRTR读写；同boot GNSS182秒仍无fix/正CNR，真实启动MCFG流程尚未重放。205蓝牙临时诊断已恢复为185；最后三个DSP running、taint/fault0。完整goal active。[206报告](../../reference/kernel206/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。' + data[end:]
lines = data.splitlines()
for index, line in enumerate(lines):
    if line.startswith('| GNSS定位 |'):
        lines[index] = '| GNSS定位 | 206同boot首次GNSS-only182.35秒，188条NMEA/176推进时间/9GSV；自动1下载/1注入到当前168h并独立复核。MM/helper签名APK203保持；206补齐modem工作文件RAM TFTP，独立及正式QRTR读写/新下载重建通过 | 真实fix/正CNR/位置事件仍0；新TFTP的正常启动MCFG流程尚未重放，不能归因定位已修复。RF/LNA/时钟/真实接收条件、精度冷启/SSR、晚到Signals/rate清理竞态、新完整rootfs和TFTP包整合仍开放 |'
    elif line.startswith('| 蓝牙 |'):
        lines[index] = line.replace('| 蓝牙 | ', '| 蓝牙 | 205两次普通启动/8轮上下电/4次重注册未复现phase5，206已恢复原185模块/helper/BlueZ并核对keys；这不是phase5修复。', 1)
status.write_text('\n'.join(lines) + '\n')
plan = dict(stage=206, goal_still_active=True, current_boot_guard='/var/lib/samurai/k205r2-runtime/boot-id-private.txt', current_transport='reference/kernel206/host.py', transition_pending=False, reboot_sent_in206=False, current_health=health, next=['Exercise TFTP block-number boundary and abnormal transfer lifecycle.', 'Prepare one fresh guarded normal reboot with newTFTP/helper hashes and ORIGINAL k200 modulemanifest; no boot flash needed. Retest actual modem mcfg.tmp/PDC/GNSS sequence.', 'Continue all camera/cellular/sensor/BT/PM/charger/peripheral gaps.'], rollback='/var/lib/samurai/k206-tftp-deploy/ original binary/helper/environment. Restore onlyTFTP; do not restartMPSS merely for rollback.', diagnostics205='All runtime/source Bluetooth changes reverted; preserved artifacts/failedGENI harness remain.', runtime_binary='d0906a5abb939fa5d1e906692b0ac769f0760857d4a9780a07ad5b59d1c4ca4e', runtime_wifi_helper='ffb65d31b337fbdad89ff9c575b133574756121f75cd2967da10f1028c1b5fbd')
(out / 'current-work-private.json').write_text(json.dumps(plan, indent=2) + '\n')
old_plan_path = out.parent / 'kernel205/current-work-private.json'
old_plan = json.loads(old_plan_path.read_text()); old_plan.update(state='Superseded by206. Both205 boots completed; diagnostic module/helper/BlueZ and hostsource restored in206. No pending transition.', next='Read kernel206/current-work-private.json and rootNEXT. Do not repeat205 reboot or load diagnostic blindly.'); old_plan_path.write_text(json.dumps(old_plan, indent=2) + '\n')
print(json.dumps(dict(stage=206, checkpoint_bytes=len(text.encode()), hardware_status_updated=True, private_state_saved=True)))
