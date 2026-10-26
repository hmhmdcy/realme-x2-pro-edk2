from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel209')
archive=repo/'archive/NEXT-SESSION-through208-2026-10-15.md';assert not archive.exists();archive.write_bytes((repo/'NEXT-SESSION.md').read_bytes())
plan=dict(stage=209,goal_still_active=True,current_host='reference/kernel209/host.py',current_boot_guard='/var/lib/samurai/k209-baseline/boot-id-private.txt',same207_second_boot=True,reboot_sent=False,transition_pending=False,
    state='One finite UTC comparison worker submitted. Originalhelper421 unchanged. Poll actualPID/cmdline and savedprogress; do not resubmit. GPS/mask cleanup is in finally.',
    next='Inspect sameworker through poll-utc-compare.py. Compare actualPQWM1 time uncertainty before/after measuredchronybound+250ms; validateACK latency vs margin and allcleanup. Only then decide product/helper/package change; no assumptionGNSSfix.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
text='''# Realme X2 Pro 阶段209进行中

完整外设goal active。208已取得原厂时钟/ADC/XTRA诊断，仍无fix/正CNR。[208完整快照](archive/NEXT-SESSION-through208-2026-10-15.md)、[208报告](reference/kernel208/README.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

当前运输reference/kernel209/host.py，guard=/var/lib/samurai/k209-baseline/boot-id-private.txt，重新核对与207第二boot相同。209尚未重启或刷写；2739.42秒三个DSP running、taint/fault0、GPS0/Signalsfalse/rate30、BT关闭无连接。旧207切换、208两个worker都已完成，不得重放。

本轮只提交了一次有限UTC比较worker，手机/var/lib/samurai/k209-tools/compare-utc-precision.py，输出k209-clock-compare；marker和PID仅在私人kernel209。用reference/kernel209/poll-utc-compare.py核对实际进程与阶段；不要因观察超时重发。它在同一MM GPS会话中先采25秒固定1000ms，再注入实测chrony误差界限+250ms余量并采60秒，finally发送一次原1000ms输入策略的当前UTC、关闭GPS、恢复原NMEA mask/刷新设置并释放CID。实际执行结果以终态收据为准。

## 源码、产物与回退依据

首次chrony实际界限178.67ms（abs(systemoffset)+dispersion+rootdelay/2），Normal/Stratum3；并非假设1ms精度。纯函数已验证毫秒向上取整、正负偏差、样本年龄/频偏及无同步/本地源/非有限/负值/过期拒绝。原厂IDL注入uncertainty单位毫秒，PQWM1 TimeUncNs单位纳秒；不把数值6秒直接当收星根因。

产品helper421、init54、MM191/签名APK203、TFTP B3/wifi854/MCFGd4均未改。Image183/boot204/DTB204、原BT185及其它部署同208。原始NMEA包含位置字段，只在私人目录；公开只输出计数及不确定度范围。本轮没有RF/供电/原厂NV操作。

## 续作与已知风险

先观察唯一worker的真实终态和清理，再按对照证据决定是否修改helper、更新可复现签名APK；不能只依据更小的输入数宣称硬件精度提高。GPS真实fix/正CNR/天线RF/天空条件、NTP启动延迟/晚到Signals竞态仍开放。

保留完整目标：相机常态sensor/PLDO冷启、真实蜂窝业务、传感器精度/SSR、BT phase5、Wi-Fi/USB PM、完整充电及其它外设、radio/Mesa APK和rootfs整合继续推进。[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。
'''
(repo/'NEXT-SESSION.md').write_text(text)
print('209 active comparison checkpoint saved;208 complete snapshot preserved. No reboot pending.')
