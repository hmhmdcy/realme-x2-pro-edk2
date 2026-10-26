# 独立 r6 USB500 诊断事务候选

只完成离线实现与实际函数测试，**未运行、未上传、未访问手机/网络/SDK**。没有修改 main、原 launcher、已实装r6、host collector 或启动脚本。根会话已实测r6更新/INHIBIT-AUTO通过；这是其后的另一项候选，不能自动执行，也不能重放旧500事务。

## 范围与复用

`worker.py` 只允许一次正常 gadget UDC解绑→临时MaxPower500→绑定，随后无论500通过/失败，都在finally尝试恢复100。仅两个 configfs 目标可写：`.../usb_gadget/samurai/UDC` 和 `.../configs/c.1/MaxPower`。网络helper仅恢复原usb0 up及已有169.254.42.1/16。没有 power_supply 写入、强制预算、CHG/INHIBIT/AUTO操作、模块加载卸载、boot/驱动/Windows供电设置/持久脚本更新。

冻结复制的 `r6-base.py` SHA `b5cfad278a1d1887e0cb38e47edcb796929b760151e5cb5bb59e775f1e2b2e98` 原样复用已审Device的fresh manager/verify/loaded-note/observe/healthy/unchanged门；不会调用其中的updater或模块控制函数。`health.py` 是已审r2 `a41942f21773c97b22d0b3760b1e256650f8e5506ee6cd0883db7145a39f4b4f` 原件，直接用于分类。两文件在import时核对exact SHA，没有device action。

已审原 `usb-reenumerate.py` **真实configure函数体**，保留其解绑、descriptor读回、2秒等待、绑定、网络恢复的顺序。新增的最小区别是每步记录和有界单次写；如果先前已完成但报错的写使UDC确实处于未绑定状态，100恢复先读回并跳过重复unbind。不会靠“命令报错”臆断它未生效。

## 新事务和主机 gate

此候选不附设备launcher。根会话审核后，才能在同boot/原SSH密钥及真实相机/蓝牙交接下，创建全新root:0700目录：

```text
/root/charging-management-20261023/usb500-r6-diagnostic-v1-<48位小写hex nonce>/
  worker.py
  r6-base.py
  health.py
  config-private.json
```

脚本及配置应root拥有、无group/world写，配置0600；不使用 `python -O`。worker自身独占创建 `execution-started-private.json` 和 `worker.pid`，launcher不得预创建这两个文件。已有marker不重放；唯一worker用新会话独立运行，SSH断开只fetch同PID/nonce/argv。

新owner lease路径 `/run/samurai-usb500-r6-window.json`，root:0600：

```json
{"transaction":"usb500-r6-diagnostic-v1","owner":"charging","camera_released":true,"bluetooth_released":true,"exclusive":true,"token":"NEW_WINDOW_TOKEN","host_trigger_nonce":"48_LOWERCASE_HEX","boot_id":"ACTUAL_BOOT","expires_boottime_s":12345.0}
```

lease须是当前BOOTTIME之后且≤180秒，仅记录根会话已有的真实交接。worker非阻塞独占原 `/run/lock/samurai-charging.lock`。前向500需要活lease；已touch的100恢复允许原lease过期、观察deadline已过或日志写失败，但仍要求原锁保留、同nonce/token/owner、同真实boot/guard、同相机/蓝牙释放记录，且只允许100阶段。到期不代表其它会话可抢手机。owner/token/boot改变时不写，不凭过期例外重试500。

`config-private.json` 固定字段示意，个体serial摘要只进私有请求，不输出到结果：

```json
{
  "transaction":"usb500-r6-diagnostic-v1",
  "guard":"/var/lib/samurai/k449-adopted/boot-id-private.txt",
  "manifest_sha256":"944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d",
  "identity":{"boot_id":"ACTUAL_BOOT","serial_sha256":"SHA256_SOC_SERIAL_RAW_BYTES","compatible_sha256":"SHA256_COMPATIBLE_RAW_BYTES"},
  "window_token":"SAME_WINDOW_TOKEN",
  "host_trigger_nonce":"48_LOWERCASE_HEX",
  "host_trigger_utc":"2026-10-23T00:00:06+00:00",
  "worker_sha256":"COPY_EXACT_TESTED_WORKER_SHA",
  "host_ready":{
    "armed":true,"armed_utc":"2026-10-23T00:00:05+00:00","target_port":7,
    "capture_id":"NEW_PRIVATE_HOST_CAPTURE_PATH_ENDING_IN_THE_SAME_NONCE",
    "host_worker_pid":1234,"remaining_seconds_at_trigger":94,
    "decoder_sha256":"9fe2ffb2792bf5feb7113167056bec4466fced9dc1b591bffbcbe8373b5e7716",
    "collector_sha256":"31c0f8e99f8ba4878b489f9b8dda34e5a688bb1e6b44415ce40a88c17fcfb6f5"
  }
}
```

根launcher必须实时读取**本轮**host ready，确认它确实Armed、对应自持PID/启动时间/命令行还活着、目标端口、源码SHA、nonce目录正确，再在ready后10秒内发起；主机采集剩余≥90秒。实际ready的PowerShell大写字段需由launcher明确映射到上述请求，不能只写一个armed=true。设备端不能自行证明Windows进程存活，JSON gate不能替代根会话这一检查。host trigger/armed时间必须是带时区、同主机时钟，间隔0–10秒；不能拿两台机器monotonic直接相减。

之前 host-01 仅有5.1秒/26轮/182返回，是失败基线的缓存，不是完整30秒或本次ready。修正版collector还须在新目录取得实时gate；本候选不能用host-01缓存直接启动。

## 实际执行与结果语义

预检固定真实r6 manifest、fresh已安装manager、全部文件与三个loaded-note、SoC serial原始bytes固定路径（无fallback）、compatible/MP client/DT、boot/guard/ABI、100mA SDP/双路输入、CC250mA/CV、fresh健康 managed或精确Full。旧fault/latch/timeout/TCA/温控等待都不能进入试验。

500阶段配置与观察最多45秒；100恢复配置后观察deadline为30秒。两阶段均要求连续12秒fresh完整健康、相邻观测间隔≤2秒；慢读缺口不累计假连续证据。500需要正常SET_CONFIGURATION/DWC3 native500、UDC configured、两输入物理500mA；descriptor500或Windowsconfiguration1不能替代预算回调。允许完整 `logical_full=hold_requested=full_holding=1`、有效cause、session_seconds0、desiredCHG0及硬件converter保持；不mask flags、不清旧fault。

每个sysfs写是一个独立子进程，最多等待3秒。完成后严格读回，已完成但报错可根据实际known state进入单次100恢复。写超时不kill、不假定结束：记录子PID，保留原worker及service锁，不发任何下一USB/network mutation。状态读回失败或不是本轮已知binding/100/500也按unknown隔离。网络helper超时先kill并确认reap；确认结束才允许100恢复，未reap则同样隔离。子进程和sysfs卡死不能被描述为“已自动回100”。

100恢复只作一次，不静默重放失败的100写或bind。若descriptor已回100但NCM网络/保护/旧锁存/Full/限值核验不合格，分别报告实际状态，不调用AUTO去消掉错误。旧fault/timeout会跨100描述符恢复保留。

`phases-private.jsonl` 对每次写前/后、配置、采样、恢复都带同nonce、realtime_ns、monotonic_ns、BOOTTIME并flush/fsync。日志写失败阻止前向500，却不能阻止已授权的安全100恢复；相应证据标为不完整，不宣称通过。`result.json` 独立保存：

- `native500_accepted`：500阶段是否拿到真实连续许可/健康证据。
- `descriptor100_bound`：最终实际读回是否已绑定100；这不等于健康充电恢复。
- `restore100_verified`：100的12秒健康/限值/环境与最终fresh样本都通过。
- `primary_error`、`recovery_error`、`final_error`、`journal_errors`：分开保存。
- `diagnostic_completed`：完成500本地阶段、100健康恢复和收尾证据；主机拒500可以使它为真，而`passed`仍为假。
- `passed`：500接受且所有恢复/收尾通过。`terminal=false`表示unknown隔离，根会话仅fetch原worker，先查明子进程及sysfs状态再明确处置，不能交回或重launch。

相机/四服务、两provider note、boot/taint、CC/CV、安装身份都需保持。沿用health的全dmesg ring计数只是**计数快照一致性门**；相等不能证明无新增错误或完整日志覆盖，ring rolloff也可能让一致性检查失败。本候选没有引入日志覆盖框架，不作更宽结论。

所有时限都依赖内核能返回必要只读I/O；进程被强杀、系统失电、内核卡住没有自动恢复保证。隔离worker不是跨boot daemon，不自动恢复或重试。

## 离线验证

`test-worker.py` 直接执行本文件实际 `transaction/configure/stable` 与冻结r6/health函数；使用根会话真实r6更新收据的完整telemetry作基线，只fake设备、时间和进程边界。51个案例覆盖普通与Full、拒500仍回100、所有500/100写/绑定失败、写已生效才报错、两个网络超时结局、旧fault/timeout保持、最后fresh故障、慢读不算连续、过期的前向/恢复分界、token/owner/真实boot改变、未知sysfs无后续mutation、journal失败的100清理及原网络helper顺序。

```text
wsl -d Ubuntu -u root -- python3 "/mnt/e/RealmeX2Pro edk2/reference/charging-session-20261023/usb500-diagnostic/device-candidate/test-worker.py"
```

这条离线测试已执行。CLI `--worker NEW_DIRECTORY`、sysfs子进程、ip及整个设备事务均未运行。
