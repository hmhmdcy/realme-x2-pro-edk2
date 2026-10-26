from pathlib import Path
import host, json
here = Path(__file__).resolve().parent; repo = here.parents[1]
old = repo / 'archive/NEXT-SESSION-through206-2026-10-15.md'; assert not old.exists()
old.write_bytes((repo / 'NEXT-SESSION.md').read_bytes())
deploy = json.loads((host.PRIVATE / 'deploy-block-fix-host-private.log').read_text())
assert deploy['block_fix_installed_and_loaded'] and not deploy['rebooted']
(here / 'tftp-deployment-validation.json').write_text(json.dumps(deploy, indent=2) + '\n')
(here / 'tftp-build-validation.json').write_bytes((host.PRIVATE / 'tftp-clean-rebuild-r2/build-validation.json').read_bytes())
(here / 'baseline-validation.json').write_text((host.PRIVATE / 'baseline-host-private.log').read_text())
text = '''# Realme X2 Pro 阶段207进行中

完整外设goal active。当前仍205第二次启动，207尚未重启或刷写；当前运输reference/kernel207/host.py，guard为/var/lib/samurai/k207-baseline/boot-id-private.txt（与k205r2-runtime相同）。[206完整快照](archive/NEXT-SESSION-through206-2026-10-15.md)保持前轮原文，不能把旧TFTP哈希当成当前部署。

## 当前部署

新TFTP b3bb82b9…已安装并运行；samurai-wifi仍ffb65d31…，32MiB私有tmpfs工作文件支持保持。内核/Image183、boot204 cdd16e29…、实际DTB b9d9c2a1…、CAMSS82cbc052…、原hci_uart185和MM191/签名APK203/helper421/init54、SSC9a1保持。没有新的NV、BT配对/连接、振动或摄像头操作。

实机独立QRTR207复现旧writer回绕后ACK错误（绝对块65539），旧reader第65537块错读；新实现用内部绝对计数/线上16位编号，1,048,603字节读回、两次回绕/四个零块号事件通过。重复DATA/ACK及原传输用例14次、26,580字节在独立和正式实例均通过。测试实例已终止/测试挂载已卸，正式缓存测试文件移除；DSP/MM/生产原服务对照保持，NV校验及故障增量0。

源代码已更新linux-port/radio完整补丁和source-lock。首次新下载构建TLS EOF保留；使用十份固定哈希源码缓存重建Werror0告警。部署首次在修改前因/usr/sbin符号链接的未规范化路径比较停止，已保留失败，修正路径与loaded hash后部署成功。没有将失败写成通过。

## 源码、产物与回退依据

当前TFTP原件在手机/var/lib/samurai/k207-tftp-deploy/samurai-tqftpserv206-original；其服务环境和PID记录同目录。206更早原程序/helper/environment另在k206-tftp-deploy。只回退TFTP无需重启MPSS。主机内核树仍204源状态，205临时诊断早已撤回；GENI源码未改，原失败harness未续完。

## 续作与已知风险

当前准备一次普通新启动以观察真实mcfg.tmp工作文件/PDC/GNSS；尚未发切换。先运行207 collect-pre-reboot，完成当前身份/分区/模块/用户态/空闲状态核对，再部署/执行quiesce和私人归档，然后只发一次已审阅RESTART2到bootloader，核对fresh fastboot后单次reboot。不需刷boot。后续以当前private/k207标记和真实状态为准，不能重复未知切换。

正常新boot的MCFG读写仍待验证；GNSS上一轮182秒188NMEA/176推进时间/自动168h辅助数据仍无fix/CNR。真实定位/RF/电源、晚到Signals/rate清理、相机常态sensor/PLDO冷启、蜂窝真实业务、传感器精度/FastRPC SSR、BT phase5/Wi-Fi/USB PM及其它外设仍开放；不能缩小完整目标。旧rootfs132与新TFTP的APK整合仍未完成。[边界](WORKING-BOUNDARIES.md)、[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。
'''
(repo / 'NEXT-SESSION.md').write_text(text)
plan = dict(stage=207, state='Block fix deployed; ordinary reboot prepared but not sent.', guard='/var/lib/samurai/k207-baseline/boot-id-private.txt', current_host='reference/kernel207/host.py', runtime_tftp=deploy['runtime_sha256'], wifi_helper='ffb65d31b337fbdad89ff9c575b133574756121f75cd2967da10f1028c1b5fbd', transition_pending=False, reboot_sent=False, finite_tests_terminal=True, next='Fresh preflight, quiesce/archive, one ordinary reboot, newMCFG/PDC/GNSS validation. No flash.')
(host.PRIVATE / 'current-work-private.json').write_text(json.dumps(plan, indent=2) + '\n')
print('207 runtime and recovery checkpoint recorded; no reboot has been sent.')
