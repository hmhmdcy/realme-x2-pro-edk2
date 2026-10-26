from pathlib import Path
import json

here=Path(__file__).resolve().parent;repo=here.parents[1]
private=Path('/mnt/e/edk2-samurai-out/kernel208')
archive=repo/'archive/NEXT-SESSION-through207-2026-10-15.md'
assert not archive.exists();archive.write_bytes((repo/'NEXT-SESSION.md').read_bytes())
plan=dict(stage=208,goal_still_active=True,current_host='reference/kernel208/host.py',current_boot_guard='/var/lib/samurai/k208-baseline/boot-id-private.txt',same207_second_boot=True,reboot_sent=False,transition_pending=False,
    state='One120s debugNMEA worker submitted, with originalmask saved and finally restoration. Check current PID/cmdline via poll-debug-capture.py; no second submission.',
    worker_submission_marker='debug-worker-submitted-private.json',next='Poll existingworker. If terminal inspectmask/GPS cleanup and diagnostic RF/clock fields. Preserve rawNMEA privately; do not repeat session just forCNR. Continue all peripheralgoal.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
text='''# Realme X2 Pro 阶段208进行中

完整外设goal active。上一轮207完成本机原厂MCFG目录和TFTP回绕修复，但GNSS仍无fix/正CNR。[完整207快照](archive/NEXT-SESSION-through207-2026-10-15.md)、[207报告](reference/kernel207/README.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

当前运输reference/kernel208/host.py，guard=/var/lib/samurai/k208-baseline/boot-id-private.txt，已重新核对与207第二boot相同。208没有重启或刷写；1097.84秒三个DSP running、taint/fault0、GPS0/Signalsfalse/rate30、BT关闭无连接。207两次切换均已完成，旧marker不得重放。

现已提交一次120秒debug-NMEA诊断worker，手机脚本/模块在/var/lib/samurai/k208-loc-tools，输出k208-debug-nmea。用reference/kernel208/poll-debug-capture.py检查实际PID和cmdline；不得重复提交。原NMEA mask63已只读查询，真实ACK/indication及CID释放/关闭通过。诊断临时增加DEBUG标志，请求完成后finally恢复原mask和GPS设置；当前是否完成以worker实际状态为准。

## 源码、产物与回退依据

原厂SM8150公开固定提交core/SystemStatus定义PQWM1时钟/ADC/增益/干扰字段及DEBUG mask0x20000；实机libqmi已有DEBUG枚举，之前旧SDK不代表当前接口。独立解析器已核对负数/小数/64位、缺省不作0、校验和/截断拒绝。公开源快照在私人kernel208/receiver-sources，来源收据reference/kernel208/receiver-source-validation.json；原始NMEA只留私人目录。

仍部署TFTP b3bb82b9…、samurai-wifi854…、MCFG复制程序d4…，boot204/Image183、原BT185/MM191/helper421/init54/SSC9a1保持。本轮尚未改产品二进制、RF/电源或NV；诊断不直接start/stop LOC引擎，由MM控制正常GPS会话。207的290文件归档及所有原厂备份保持。

## 续作与已知风险

先观察唯一worker终态，确认掩码和GPS恢复，再依据实际PQWM1字段缩小接收器/时钟/RF方向；不能把时间推进当作定位。若未收到debug数据，只据真实ACK/响应分类，不盲改NV、GPIO或供电。

GNSS真实fix/正CNR、初始化/RF/天空条件、NTP启动延迟与晚到Signals/rate、完整radio包/rootfs、相机常态sensor/PLDO冷启、蜂窝真实业务、传感器精度/SSR、BT phase5、Wi-Fi/USB PM及其它外设仍开放。[完整硬件清单](linux-port/docs/HARDWARE-STATUS.md)。
'''
(repo/'NEXT-SESSION.md').write_text(text)
print('208 live worker checkpoint recorded;207 snapshot preserved; no reboot pending.')
