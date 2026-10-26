# R7 → R8 专用两文件更新候选

本目录只有离线代码、23 组受影响分支验证和审计记录；没有访问手机、SSH、USB、SDK 或共享 source/build。`update-r8.py` 从冻结、已有 67 例实测的 r6 更新事务定向迁移；旧 67 例没有重新运行，也没有将旧收据改名成 R8 测试。`migration.patch` 提供完整差异，`prepare.py` 核对旧源 SHA 后可再生成同一候选。

| 对象 | 固定值 |
| --- | --- |
| 当前 R7 manifest | `5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68` |
| R8 manifest | `320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f` |
| R8 charger ko | `10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f` |
| 冻结 tar.gz | 51,100 bytes；`f2bcbe500463114a407d93ddb4e2081db179f61dcc35d0a194abb4d18b2a5722` |
| service（只读） | `/usr/sbin/samurai-charging`，0755，`61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4` |
| worker SHA256 | `479916c260c7ee9c654ba6471ec22f3ece67d5d797d2de03d5d5e199ee80814b` |

载荷和所有替换/恢复代码只接受两个 root:0600 普通文件：

- `/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko`
- `/usr/share/samurai-charging/manifest.json`

service 只核对字节、0755 mode 和 manifest 身份，不备份为写入对象，不替换。manifest 除 revision=`r8` 和 charger 摘要外必须与 R7 完全相同；USB/protection/service/init/library/boot 项不能改变。不执行 depmod、rc-service、USB 重枚举、PM 或 boot 操作。仅 charger 卸载/载入；两个 provider 始终驻留并前后核对 loaded-note。

## 根 launcher 的固定契约

根会话在摄像头/蓝牙真实交回后创建新的 root:0600 lease：`/run/samurai-charging-r8-window.json`。不得复用旧 lease/token/终态目录；lease 不替代真实交接。

```json
{"transaction":"charging-update-r8","owner":"charging","camera_released":true,"exclusive":true,"token":"UNIQUE_TOKEN_32_TO_128_NON_WHITESPACE_CHARS","boot_id":"CURRENT_BOOT_UUID","expires_boottime_s":12345.0}
```

有效期为当前 BOOTTIME 之后且不超过 300 秒。原 SSH key、当前已观测 IPv6 peer/HostKeyAlias 和当前新 boot 由根 launcher 验证；本 worker 不含网络连接。新 guard 固定为 `/var/lib/samurai/charging-r7-8162b1e7040030d514a83534-adopted/boot-id-private.txt`。原 R6 的八字段 JSON schema 保留，仅固定身份迁移到 R7/R8：

```json
{
  "transaction":"charging-update-r8",
  "guard":"/var/lib/samurai/charging-r7-8162b1e7040030d514a83534-adopted/boot-id-private.txt",
  "identity":{"boot_id":"CURRENT_BOOT_UUID","serial_sha256":"LOWERCASE_SHA256","compatible_sha256":"LOWERCASE_SHA256"},
  "window_token":"SAME_UNIQUE_TOKEN_AS_LEASE",
  "old_manifest_sha256":"5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68",
  "new_manifest_sha256":"320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f",
  "payload_sha256":"f2bcbe500463114a407d93ddb4e2081db179f61dcc35d0a194abb4d18b2a5722",
  "payload_base64":"EXACT_FROZEN_PAYLOAD"
}
```

`serial_sha256` 是 `/sys/devices/soc0/serial_number` 原始完整 bytes（含换行）的摘要；compatible 同样使用原始 bytes，不使用其它 serial 路径 fallback。只从原 key 验证的当前连接取身份摘要，私有存储个体值。ABI 固定 k363，guard 和 request boot 必须匹配当前 boot。

唯一执行命令为 `python3 update-r8.py --execute-r8`，不得 `python -O`。worker 从 stdin 接受请求，非阻塞占用原 `/run/lock/samurai-charging.lock`，独占新建 `/root/charging-management-20261023/charging-update-r8`；目录已存在直接拒绝，不删除重放。根 launcher 采用固定 runner/request/PID/log 路径、脱离 SSH transport 的单次子进程与文件日志，记录 PID+startticks。SSH 超时或不确定发起结果只能 fetch 同一进程/终态，禁止再 launch。当前 guard/identity/lease 和本收据 `tested_files['update-r8.py']` 均须在发起前核对。

## 顺序和安全边界

预检使用磁盘 fresh manager，verify 整份 R7 manifest 和三个 loaded-note，要求 fresh 完整无 fault/latch/timeout/TCA/OCA/温控抑制样本、taint0、四个 UID10000 用户服务、相机 PM/m2m idle、OpenRC started。限定当前真实 SDP100，分别核对 raw native `input_current_limit`、有效预算 `current_max`、sample `budget_ua`、两物理输入限值均为 100mA；CC250mA，温度处于 NORMAL 的 16≤T<44℃。这只限定本次更新窗口；预算验证仍使用有效 source 额度，没有把真实 CDP1500 错压成 raw native100。

旧 manager 同步 stop 且 REG08 两控制位读回 INHIBIT 后，再读 fresh 无故障样本，随后卸载 charger。原子写入两文件、显式 insmod、重新加载同一只读 service、verify R8 和三 note。新 module 在 INHIBIT 下必须先得到 fresh 完整安全样本，才调用既有 manager.start(AUTO)。仅 probe 的 `valid=0,error=-ENODATA` 且其余 fault/latch/stop/timeout/抑制位全零可最多等 3 秒；其它异常立即拒绝。样本和 REG08 读取不是原子内核事务，因此不能承诺最后一次安全读与 AUTO 之间绝无新异步故障；内核自身保护仍是控制权威。

验收必须保持两输入、CC、继承 CV、raw native/有效预算与 R7 完全一致，并得到 R8 `thermal_band=4`/`band_pre_shake` 字段。普通 managed 或精确健康 Full 可通过：Full 的三状态位一致、cause1..3、desired0、session0、REG08 控制位0；部分或矛盾 Full 不通过。相机状态、四 PID/UID/comm、boot、taint0、两个 provider note、OpenRC 标志均须不变。软件模拟验证不能替代实机验收。

任何停止失败或 stop 后出现旧 fault/timeout，均保留 R7 module/files，不卸载。进入更新后若读到任何 unsafe 样本，即使下一次读取恢复正常，也不能据此卸载/重新 AUTO。先同步 INHIBIT；若当前 manifest/service/loaded-note 一致，保留一致的 R8（或 R7）并报告 `passed=false`，等待根会话决定。只有安装确已不一致、需要修复磁盘的情况，才恢复旧两文件而保留现 live module；结果明确记录 `repaired_disk_files` 与 `runtime_disk_mismatch_requires_review=true`，不当成正常回退或通过。已知且无 unsafe 样本的普通安装失败才可停充、卸载、恢复 R7 两文件、fresh verify/load、再次取得安全 INHIBIT 样本，并在当前有效 lease 内按实际 source 预算恢复 AUTO。恢复二次失败仅尝试一次 live-module safety stop，保留 primary/stop/recovery 错误。

unknown mutating 子进程、coming/going 或无法确定的 module 状态将 `terminal=false`、保留 service lock，不 kill/retry/rollback。遇 unknown 后 manager 操作和磁盘恢复均拒绝；即便 stdout/receipt 写失败，CLI 也保持该隔离 worker 被动等待。只能由根读取同 PID/child/module 实际状态后明确决定下一步，不能自动交回其它会话。

重载按已有驱动语义重新初始化易失 session/full/thermal 历史；候选记录更新前 `session_seconds` 和 `volatile_cycle_reload_boundary=true`，没有伪造旧 timer、没有新增跨 boot 永久到期机制。已建立或本次观察到的 timeout/fault 都不允许走这条重载路径。它也不承诺掉电或被强杀后的自动恢复。

## 离线验证

`test-update-r8.py` 执行实际 update/健康/manifest/载荷和选定 Device 函数，只 fake 文件/manager/kernel/process 边界；AST 只取旧 Fake 类，不执行旧测试主体。使用已收 R7 试验末态真实 sample/limits/四服务作为 fixture，额外覆盖两成员白名单、service 零写入、当前 NORMAL100 输出相同、原 fault/timeout 拒绝、新故障保留一致版本、先 unsafe 后 good、真实不一致磁盘修复、两次恢复 stop 错误、两文件安装边界、原预算与 CDP 有效额度区分、未知进程/模块/输出失败锁隔离、新 guard/lease、fresh manager 代码绑定。23 组均通过。

```text
wsl -d Ubuntu -u root -- python3 "/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/r8-update/test-update-r8.py"
```

`test-result.json` 给出实际 worker/test/生成脚本、旧冻结输入、R7 fixture、载荷的摘要及运行范围。尚未部署；根 launcher 的交接、当前身份和唯一运行/fetch 负责现场约束，本目录不会申请或占用手机窗口。
