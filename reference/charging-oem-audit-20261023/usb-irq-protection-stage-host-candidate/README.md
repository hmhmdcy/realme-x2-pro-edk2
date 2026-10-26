# IRQ + 保护查询 cohort：只暂存的 host 候选

只服务于独立新 `usb-irq-protection-stage-*` 事务：将已冻结的两个 ko 和 manifest 载荷交给配套 stage worker。该 worker 暂存到磁盘，原三个模块继续驻留且充电保持 INHIBIT；成功只表示 **staged/runtime_pending**。没有重启、boot/logdump 写入、模块热卸、自动启充或保护查询入口。本轮工具未联网/执行暂存，未创建实际 runtime request，也未改当前 pointer 或 prepared 502 事务。

`host.py` 默认 `check-local` 只核冻结源码/worker/cohort 载荷，不要求或生成未来 boot 身份。`source-pins.json` 只绑定已有源码和物料；它不是运行许可。原502 adoption `review()`、postboot audit/原件/执行源码复用，未重跑其旧测试。

## 实际使用顺序（由 root 安排当前独占窗口）

以下在 WSL 中使用，原 strict key、IPv6 peer29 和 HostKeyAlias 固定，无 fallback。常规修复授权沿用，`--window-confirmed` 只表达 root 已取得相机/蓝牙释放后的当前独占窗口，不增加一般审批门。

1. 先完成真实 `image502-notify-live-001` 的完整 postboot 和 adoption。需要 #502、新 boot、boot97811/logdumpace2、原 R8 磁盘/驻留 notes、相机481/468和完整保护/源预算证据，以及当前 global pointer 和原 key 的真实新 endpoint。仅 prepared、旧501/guard、手填 passed 或缺任一实际原件均不可替代。
2. 默认离线检查：`python3 -B host.py`。随后对**新的唯一**事务执行本地 bind：

```sh
python3 -B host.py --action bind \
  --transaction usb-irq-protection-stage-live-001 \
  --context <502实际事务/host-context-private.json> \
  --postboot-directory <502同事务实际passed postboot目录> \
  --adoption-directory <502实际事务/adoption-01-private>
```

bind 先调用冻结 adoption review 重审真实 postboot/context，再核 actual adoption 执行源码、原 child terminal0、回复、请求、结果、endpoint 和当前 pointer 的精确关系。全部通过后才创建新私有事务目录和 request；缺真实502证据在 mkdir/request 前拒绝。guard hash 是已核 adoption payload 所写确定字节 `actual_boot_id + newline` 的期望 hash，设备端仍必须对实际 guard 文件读回对照。host 不填造尚未取回的 fresh-proof hash；worker 自行读取并核验 guard 同目录的实际验证原件，记录其实际 SHA。

3. root确认当前窗口后显式单次启动：

```sh
python3 -B host.py --action launch --transaction usb-irq-protection-stage-live-001 --window-confirmed
python3 -B host.py --action status --transaction usb-irq-protection-stage-live-001
python3 -B host.py --action fetch --transaction usb-irq-protection-stage-live-001
```

launch 重核绑定原件（含当前 pointer 未变），先永久保留本机一次 intent，再以固定原 key 传输。远端先核同 boot/guard，独占创建事务目录与 claim，写一次120秒 BOOTTIME lease，启动唯一 detached supervisor。supervisor 的 stdin 为 DEVNULL；worker 的 stdin 是已 fsync 的 request-private.json **普通文件 fd**，不会随 SSH 断开而变空。两者 stdout/stderr 都是普通私有日志。lease 不由 bind 猜时间，也不续期。实际 worker argv 为 `python3 -B /root/charging-management-20261023/<tx>/stage-worker.py --execute-stage`；它不启动其它 child。

host 等待本次确切 SSH child 的真实终态，不 timeout kill/自动重发。独立 supervisor 另持有唯一实际 worker Popen，即使发布 PID receipt 失败也在 finally wait 同一 child，持久化其真实 rc/terminal；不把 PID absent 或 SSH rc0 当作 worker 成功。任何断线、非零退出、缺回包或启动后未知都保留原 intent；同事务再次 launch 拒绝，只能 status/fetch。远端 supervisor→worker receipt 的 PID/start_ticks/argv 与实际 /proc 对照；若原 PID 无法证明则保持 unknown。一个只读 status/fetch transport 不是新 stage worker。

status/fetch 不调用 worker、不写 lease、不修改充电或文件载荷。当前 pointer 后续变化或源 boot 已结束，不会阻挡原 request/claim/source 所绑定事务的原件取回。只有 launch 必须当前同 boot/guard；新 boot 时明确 process=source_boot_ended，不读当前同 PID，无法核 boot/guard 则保持 unknown，均不授予重启或重试。部分/畸形 result JSON 记录观察错误并取回原始字节，不当成成功，也不删除/覆盖未知终态。原件保存在该次独立 fetch 目录；stdout 只给摘要，不输出载荷/完整私有采证。

## 成功后的边界

仅在实际 worker 结果及原 child 收敛后交 root 审阅 `staged/runtime_pending`。host 本身始终输出 runtime_validation_accepted=false；没有将磁盘写成功冒充新模块驻留、IRQ 可用或新查询兼容。

**不得复用旧502 controller/quiesce/restart。** 暂存成功后是新 disk/manifest、旧 resident notes，旧 manager 的 loaded_matches 应当拒绝；不能绕过它伪造运行一致。后续重启必须另建专用新 guard/事务，并只读核对源 stage 实际终态、当前 INHIBIT/REG08、旧 notes 与新 disk，才能进入后续设计的重启工具。本叶没有实现此路径或载体写入。

定向测试只覆盖新增 host 证据比较、缺真实 postboot 零 request、pointer 漂移、未知单次 launch/同 child fetch，以及部分结果原包保留。硬件、传输、进程和保存身份边界明确 fake；不生成实际未来 boot/guard/request，不重跑 worker/cohort/旧 postboot/adoption 矩阵。最终源码、物料和真实测试收据以 `delivery.json` 为准。
