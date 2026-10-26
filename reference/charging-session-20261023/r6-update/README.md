# r5 → r6 专用更新事务候选

本目录只完成离线实现与测试，没有访问手机、SSH、SDK、共享 kernel/source/build，也没有修改 main、冻结 v1/v2 或安装文件。根会话另行准备的 launcher 负责现场交接和唯一 worker；本文件本身不提供网络访问。

`update-r6.py` 只接受显式 `python3 update-r6.py --execute-r6`，标准输入为下述 JSON。禁止用 `python -O`；原已安装 service 的 verify 仍使用断言。

## 固定输入和安装范围

| 对象 | SHA256 |
| --- | --- |
| 已安装 r5 manifest | `f1a885e2ca9c3226ca50d94f39c17c3cae5411b1047696976975df976aa971cf` |
| r6 manifest | `944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d` |
| r6 tar.gz，54,604 bytes | `2433d8c04d22bb3e88eb1a2f0ea15c3fc3285706c40695fac6ce605613c57d58` |
| 新 charger ko | `fac827cfd3d1d847cb1db82f0a29e451652bd16a996b20666be2d9b330889cb6` |
| 新 service | `61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4` |

tar 不解压到文件系统：先检查完整载荷和每个成员的散列、恰好三个 regular 文件、root owner 与 mode，再在内存读取。安装目标仅以下三个文件：

- `/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko`，0600。
- `/usr/sbin/samurai-charging`，0755。
- `/usr/share/samurai-charging/manifest.json`，0600。

核对旧文件实际 mode，备份字节与 mode，原子替换时保留它们，包含 fsync；恢复也使用相同 mode。现有同名模块没有新依赖，直接 insmod 指定路径，不执行 depmod，不改模块索引。USB、保护模块、OpenRC 脚本/开机项、USB 描述符、boot、原厂寄存器备份、NVM 都不在写入列表中。只另建事务审计目录和复用原 service 锁。

## 前置与唯一执行

根会话必须先取得相机/蓝牙的真实明确交接；lease 只是对此事实的防重叠记录，不能替代交接或赋予授权。root launcher 可随后创建 root:0600 `/run/samurai-charging-r6-window.json`：

```json
{"transaction":"charging-update-r6","owner":"charging","camera_released":true,"exclusive":true,"token":"ROOT_GENERATES_UNIQUE_AT_LEAST_32_CHAR_TOKEN","boot_id":"ACTUAL_BOOT_UUID","expires_boottime_s":12345.0}
```

有效期必须在当前 BOOTTIME 之后且不超过 300 秒。未知旧事务结果只能 fetch 同一 worker/PID，不能重新 launch。本事务非阻塞获取原 `/run/lock/samurai-charging.lock` 并独占创建 `/root/charging-management-20261023/charging-update-r6`；该目录已存在时不执行更新，失败也不得删除后重放。

请求 schema（字段名固定，摘要均为原始字节 SHA256）：

```json
{
  "transaction":"charging-update-r6",
  "guard":"/var/lib/samurai/k449-adopted/boot-id-private.txt",
  "identity":{"boot_id":"ACTUAL_BOOT_UUID","serial_sha256":"64_lowercase_hex","compatible_sha256":"64_lowercase_hex"},
  "window_token":"SAME_UNIQUE_TOKEN_AS_THE_OWNED_LEASE",
  "old_manifest_sha256":"f1a885e2ca9c3226ca50d94f39c17c3cae5411b1047696976975df976aa971cf",
  "new_manifest_sha256":"944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d",
  "payload_sha256":"2433d8c04d22bb3e88eb1a2f0ea15c3fc3285706c40695fac6ce605613c57d58",
  "payload_base64":"BASE64_OF_THE_EXACT_FROZEN_TAR_GZ"
}
```

当前 revision 2 的 `serial_sha256` 只匹配 `/sys/devices/soc0/serial_number` 的原始完整 bytes（含 sysfs 换行），且必须非空。此为 Qualcomm socinfo 导出的硬件 SoC 序列来源，不对 DT 或任何其它路径作 fallback。根会话在原 SSH 密钥验证的现有连接中读取该路径并仅将摘要放入私有请求；不在公开文档/结果输出个体串号或个体摘要。实际 root 预检发现原 DT 节点缺失时尚未产生充电 mutation；旧 DT 版代码/收据保存在 `revision-dt-serial/`，不得执行。

另核对 compatible、精确 k363 ABI、boot/guard、真实 MP2650 client/DT 路径、root、OpenRC 已 started、taint0、旧七文件 manifest 及三模块实际 loaded-note。SoC identity 不替代 SSH 身份核验。预检要求 fresh 完整正常充电、无旧 latch/fault/timeout、原 native/input100mA 和 CC250mA。stop 后再检查一次完整无 fault 样本，随后才允许卸载。

已只读核对现有 `/mnt/samurai-full282/source354`：`drivers/soc/qcom/socinfo.c` 的 probe 通过 `qcom_smem_get(...SMEM_HW_SW_BUILD_ID...)` 获取 socinfo，先检查返回长度覆盖 `serial_num`，再将该 little-endian 32位字段按 `%u` 放入 `soc_device_attribute.serial_number` 并 `soc_device_register`。`drivers/base/soc.c` 仅在该属性存在时导出只读属性，`soc_info_show` 按 `%s\n` 输出。因此摘要必须包括换行；这不是读取 DT serial，也不构成独立密码学设备认证。完整来源路径/源码散列见 `soc-identity-source.json`，没有保存个体串号或个体摘要，没有绑定 SDK。

## 实际顺序与验收

锁内 fresh runpy 加载磁盘旧 manager，执行其 stop 并读取 REG08 证明 INHIBIT；不启动 rc-service 子进程来重入同一锁。卸载 charger 后只替换三文件，显式 insmod 新 ko，重新从磁盘加载新 service、verify 新 manifest、核对三个 loaded-note，再调用该新 manager 的 start。manager 对象绑定 service 摘要，verify/start/stop 都拒绝旧内存代码匹配新文件的情况。

OpenRC started marker 保持，原输入/充电请求仍为 900/250mA。实际输入必须同时受实时合法 native/source 预算限制，两输入硬件限值必须一致。恢复使用旧 manager 的同一策略，绝不调用历史 rollback 或盲写原 Android 大电流寄存器。本轮100mA的前后预算必须相同才验收；中途合法预算变化不表示内核违规，也不能凭前后读数声称预算从未变化。

可接受两种结束状态：fresh 完整普通 managed，或 `logical_full=hold_requested=full_holding=1`、有效 Full cause、`desired_enable=0`、`session_seconds=0` 且 REG08 两控制位为0的健康 Full 保持。所有错误/保护/锁存/timeout/来源/TCA/OCA检查优先。热等待、gauge stop、未知来源、部分矛盾 Full 字段都不算通过。CV 不能高于更新前继承上限；相机 PM/m2m、四用户服务、boot、taint0、两个驻留 provider note 和 OpenRC 状态都需保持。

## 失败、恢复和未知状态

- stop 抛错、硬件未确认 INHIBIT，或 stop 后新出现 fault/timeout：保留旧模块和文件，不卸载。
- 普通已结束的更新失败：用当前磁盘上已知 service 的 fresh stop，确认硬件安全后卸载 charger，恢复旧三文件/原 mode，fresh 旧 service verify、显式载入旧 ko，再按当前预算恢复 r5。新增 fault/timeout 或无法得到完整保护样本时恢复 r5 但保留 INHIBIT，记录故障样本并拒绝 AUTO；不会用重载自动清故障重新充电。
- 恢复自身失败：分别保存 `primary_error`、`stop_error`、`recovery_error`。能确认 live 且无未结束子进程时只作安全 stop；不继续重复卸载/加载。
- mutating 子进程30秒超时，或模块处于 coming/going/无法判定状态：记录 PID/命令和 `terminal=false`，不 kill、不回退、不重试。原 worker 保持 service 锁被动等待；根会话仅 fetch 同 PID。必须先确认子进程真实结束、模块 live/absent 与安全状态，再明确决定如何结束隔离 worker/开启新的恢复事务。不能把此结果当作已完成更新，也不能释放手机给另一会话。

`result.json` 还保存最终磁盘三文件的实际摘要/mode；`passed` 表示本次 r6 完整验收通过，成功恢复 r5 不会改写为 passed。新旧 loaded-note、原样本、备份 mode 与过程信息保存在同一私有事务目录。终态报告不证明掉电/进程被强杀后的自动恢复；本候选不增加跨 boot daemon。

## 离线验证

`test-update-r6.py` 直接导入、执行实际 `update()`，只 fake 文件/模块/manager/硬件/子进程边界；基线 sample 来自 main 实际 `charger-update-result.json`，使用生产 `session_seconds`。另直接执行 Device 的原子写/恢复 mode、失败 fsync 清理、stale manager 拒绝、lease/boot/token/过期、coming/going 和 Popen 超时隔离函数。

67 个定向案例通过，保留原65个安装/停充/回退等案例，并新增实际 `Device.begin` 中固定 SoC serial 缺失和不匹配两项拒绝测试。两项都故意放置匹配 DT serial，确认不能 fallback，且锁/事务目录尚未创建。覆盖每一安装写入/加载/验证/启动失败边界、安全停失败、旧及新 fault/timeout、恢复次级失败、精确 Full、预算/CV/相机状态变化，以及未知进程不产生后续 mutation。`test-result.json` 同时提供 `candidate_files` 与 `tested_files` 摘要供 launcher 检查，记录 revision 2 和上一收据摘要；也核对冻结 v1/v2 文件和 main service/updater 摘要。

复跑（仅离线）：

```text
wsl -d Ubuntu -u root -- python3 "/mnt/e/RealmeX2Pro edk2/reference/charging-session-20261023/r6-update/test-update-r6.py"
```
