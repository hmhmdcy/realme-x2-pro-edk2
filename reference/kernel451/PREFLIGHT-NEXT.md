# 451／452：统一只读 preflight 与交接入口

2026-10-23。[preflight-handoff.py](preflight-handoff.py)已离线完成，[检查收据](preflight-offline-validation.json)通过语法、只读查询边界和26个反例。本代理没有SSH或手机读写，离线结果的 `fresh_preflight_verified=false`。主线已收到充电的明确交回，并提供新的私有owner-return；实际preflight仅由主线执行。

脚本现已冻结。未改451／452原有文件；特别保留452钉住的451 body SHA `a65f6326…e279fff`、observer SHA `3a5716a6…f3fe50`及两者构建指纹。不可变输入使用独立 `immutable-inputs-v2-private.json`；动态comparison／diagnostic计划、硬件和运行收据、README及主线staging脚本不纳入冻结，以允许合法准备下一事务。

## 默认行为与现场查询

不加 `--live` 时只在PC私有 `kernel451/preflight-handoff/` 渲染 `query-private.py`，不导入SSH transport。没有owner-return时生成的脚本在任何设备查询之前直接拒绝执行。`--self-test`额外写本页链接的脱敏离线收据；合成反例不生成baseline或handoff，不作为实机证据。

只提取441 preflight中 `code` 字面量的只读baseline查询，将末尾打印改成返回baseline；没有执行或复制其后创建boot guard的代码。充电读取只复用冻结451 body的 `sha()`／`charging()`定义，继续由已安装 `samurai-charging` 的 `verify()`／`loaded_matches()`核对当前manifest、三常驻模块文件与loaded note。

实际查询先要求现场完整boot与owner-return相同，且既有 `/var/lib/samurai/k449-adopted/boot-id-private.txt` 实读逐字节等于 `/proc/.../boot_id`。guard不存在或不等即失败，不创建、不重新采用。随后核对：

- 正式440 r32／r27七个包、八份正式安装文件，以及正式libcamera SHA `0884c734…5849a48`；模块来自正式434安装证明，与440／444恢复依据一致。
- 三个正式模块磁盘SHA、实际modinfo路径、磁盘ELF note与loaded note、in-tree属性及无test参数。
- m2m无运行／用户／失败／未完成作业，core供电、DMA、映射与导入资源全部释放；四个相机平台设备suspended，taint0。
- PipeWire与WirePlumber各一个非僵尸进程，实际四个Uid均10000，保留PID与start_ticks私有身份。
- 当前充电十字段完整快照，开关有效，查询前后严格相同；manifest与owner提供的完整原件SHA相同。owner若额外提供charging对象，还须逐字段相等。

远端仅调用只读modinfo子命令，使用 `python3 -B`，无stage／launch、创建目录或文件、停止服务、模块切换、USB动作及guard写入。完整身份、进程和充电数据只写PC私有目录。查询随机request_id和owner文件SHA绑定同次返回，成功后再次核对owner文件未变。

## 主线可信 owner-return

本次主线已生成 `/mnt/e/edk2-samurai-out/kernel451/owner-return-r5-private.json`，无可选charging对象，离线结构／文件SHA校验通过。后续owner-return必须由主线真实协调生成，不能因USB恢复、旧boot摘要或设备可连而推断交回。必需字段为：

| 字段 | 要求 |
| --- | --- |
| `schema` | `samurai-camera-owner-return-v1` |
| `return_id` | 本次交回的唯一安全目录名，1—80个字母／数字／点／下划线／连字符 |
| `issued_at_utc` | 带时区的实际交回时间，不能在未来；执行时一小时内 |
| `from_owner`／`to_owner` | `charging`／`camera` |
| `released`、`original_key_verified`、`charging_worker_exited`、`no_concurrent_owner` | 全部严格为true，来自主线实际交接确认 |
| `authorized_window_ids` | 明确列出允许的451／452窗口，不接受笼统USB已恢复 |
| `boot_id` | 完整UUID，不能填摘要前缀 |
| `boot_guard_path` | 精确既有k449 guard路径 |
| `charging_manifest_private`／`charging_manifest_sha256` | PC私有完整manifest原件及实际SHA，不能只交一个摘要常量 |
| `provenance_private`／`provenance_sha256` | 本次恢复／交回完整私有证据及实际SHA；主线确认其terminal、worker退出、健康与同boot语义 |
| `charging` | 可选；若提供，必须是451既有十字段的完整实际快照，不能按旧snapshot猜值 |

脚本检查owner的授权布尔值、时效、窗口、完整boot、私有原件存在与SHA；provenance本身验证为对应JSON原件，其恢复健康语义由主线可信收据负责。它不是自行推断交接的工具。若owner再次转交、boot或manifest变化，旧owner-return立即不再适用；不能只更改旧文件时间来延长授权。

## 精确入口与输出

以下仅供主线执行；本代理未运行这些 `--live` 命令。每个窗口分别实读一次，生成自己的baseline。完成451并恢复正式栈之后，再为452查询，不能复用451的旧作业计数。

```sh
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel451/preflight-handoff.py' \
  --window-id k451-proxy-comparison-r1 \
  --owner-return /mnt/e/edk2-samurai-out/kernel451/owner-return-r5-private.json --live

python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel451/preflight-handoff.py' \
  --window-id k452-full-diagnostic-r1 \
  --owner-return /mnt/e/edk2-samurai-out/kernel451/owner-return-r5-private.json --live
```

本次 `return_id=charging-r5-recovery-to-camera-20261023`。各窗口输出目录为：

```text
/mnt/e/edk2-samurai-out/kernel451/preflight-handoff/k451-proxy-comparison-r1/charging-r5-recovery-to-camera-20261023/
/mnt/e/edk2-samurai-out/kernel451/preflight-handoff/k452-full-diagnostic-r1/charging-r5-recovery-to-camera-20261023/
```

成功才在对应目录写 `observation-private.json`、`baseline-private.json`、`charging-snapshot-private.json`及 `handoff-private.json`。handoff精确沿用 `samurai-camera-handoff-v1` 的既有字段，绑定同次baseline文件SHA、正式库SHA、实际充电快照及窗口，供451 `prepare-comparison.py`或452 `prepare-diagnostic.py`的 `--handoff`／`--baseline`入口使用。已有成功handoff拒绝覆写；失败不写成功baseline／handoff。脚本没有stage或launch功能，后续由主线独立显式执行。

离线反例覆盖交接未释放／错owner／原key未确认／worker未退出／并发owner、陈旧授权、未授权窗口、guard错误、boot摘要，以及返回nonce、owner SHA、boot、taint、正式库／包／模块／note、活跃m2m／core／PM、错误服务身份和不完整充电快照。自检只证明这些软件边界；下一窗口的实读成功与451／452硬件结果须分别记录。
