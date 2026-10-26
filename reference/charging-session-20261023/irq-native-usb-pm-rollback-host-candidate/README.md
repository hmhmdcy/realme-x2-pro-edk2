# 当前 USB PM 冷回退：原动作审核与请求绑定

2026-10-24。仅离线完成，未连接手机、生成实际事务或执行回退。对应[三分支设备执行器](../irq-native-usb-pm-cold-rollback-candidate/README.md)6818939b；继续复用原严格密钥、原 R2 传输审核和已保存来源审核，不要求候选新系统整套验收先成功。

## 已接通

- `saved-proof.py` 按实际保留的十七份 stage 原件核来源，再审核原单 logdump 工具的命令、输入、输出与真实子进程终态。`saved_command` 原函数逐字复用，`review_action` 只换当前 schema 和固定 operator 路径。重放只调用保存的输出，不能派发 fastboot。新系统分支要求选定写入先于重启、重启绑定该次写入；后续相反操作、未决或部分旧动作拒绝。
- 来源已跨 boot 时只复核该次留存 source；当前全局 adoption pointer 不参与过去事实判断。原七文件启动上下文、源码、guard、身份和 stage 对应检查仍保留，SSH255 仍不是启动成功。正向执行继续使用当前 pointer 门，不能借此入口派发历史动作。
- `current-probe.py` 只读当前实际内核、两个完整载体、三驻留 notes、模块状态和保护缓存。缓存必须是同一个已绑定实例，保持只读 fd，前后身份/缓存一致；未捕获0/0或已终态1/1均可，捕获中1/0拒绝，不启动新的 MAC 查询。
- `bind.py` 审核原严格密钥、固定 `-C`、真实同一 child/输入输出和 wait0，再运行实际设备端 profile 校验与6ff66d18逆向包解包。三种分支分别为：同 boot 502/ace2旧驻留、504/4453新驻留、502/ace2新驻留。当前 probe 不合格或原来源不存在时，在创建输出前拒绝。

`bind.bind(out, transaction_id, profile, stage_directory, stage_fetch_directory, probe_directory, context_path=None)` 仅在全部审核后写新私有目录内的 request、原 worker 和 binding；未写 lease、未 launch，也不把这次只读快照视作之后执行时的新鲜健康证明。新 boot 两分支必须提供实际原启动上下文；同 boot 分支不能带启动上下文。

`bind.probe_payload(...)` 返回固定来源绑定的只读程序，`bind.transport_argv()` 给出原严格密钥固定压缩参数。本叶尚无实际传输 owner，不能仅靠这些 API 宣称可部署。默认运行三个入口仅检查本地源码，无手机访问。

## 定向验证

七组覆盖当前改动：原函数复用、只读 probe 夹取及失败清理、三分支实际 request/逆向包绑定、当前错误组合拒绝、七文件过去上下文、原工具两组动作回放和未决拒绝、缺少真实 stage 时不创建输出。仅设备/来源/进程 IO 边界建模；使用真实原 R2 回执审核、实际 profile 校验、固定逆向包和原 operator 函数。

首轮七组中五组通过，两处夹具错误保留在 `history/test-attempt-1/`：源码对照误用更早 schema；Python 字典共享引用不能模拟独立 JSON 观测。只修夹具并重跑两组，均通过；另外三个默认入口通过，原 child 均实际 wait0。不是实机三分支回退证明，也不重复旧全量矩阵。

## 下一步

复用现有连接式回退的同 child 监督、transfer/status/fetch，绑定当前6818 worker、source observations与当前cache；补齐恢复后载体/正常重启和新 boot 验收。成功写回两文件仅是 `staged_original/runtime_pending`，必须恢复ace2并正常启动、核对旧驻留后才是完整恢复。当前手机最近确认仍502/edd/ace2、7cb/97c/7848/18e8；未热卸USB、不AUTO清Full、不改桌面和相机。
