# 477：目标真实 providers 的只读 APK 解算准备

本准备代理仅本地准备，未访问手机或 SDK。主线首次实际 stage 在授权 age510.993秒超过480秒上限时拒绝，发生在 mkdir、文件写入、worker 或 APK 之前；未重试，未执行目标 solver，设备已交回。保留 r1 物料与原始失败日志。475 缓存 rootfs 缺五项 providers 的失败保持原样。

`prepare-runtime.py` 逐字节绑定 475 `candidate-state.json`、七包报告及 r2 manifest 中的签名索引。复制既有 r33/r28 七包和索引，不编包、不签名。`target-worker.py` 运行实际目标 apk3.0.8 `verify`，成功后才运行精确七包 `add --simulate --no-network`；私有 repositories/cache/tmp，关闭 scripts、commit-hooks、交互、全局 logfile。现有系统信任集只读，验签或 solver 失败不绕过。

当前私有准备目录为 `E:/edk2-samurai-out/kernel477/k477-target-deps-r1-bound`。主线检查后依次执行：

1. 用既有严格原钥传输运行 `stage-query.py`，标准输入必须为同目录 `payload-private.tar.gz` 的二进制流。它验证归档 hash/完整成员集/每文件 hash，创建唯一目标 `/var/lib/samurai/k477-target-deps-r1`，root:root、目录0700/文件0600；已有目录拒绝覆盖。
2. 独立运行 `launch-query.py`。只启动一次；保存 PID/start-ticks。`observe-query.py` 只报告同一进程与终态，禁止重启/重放。
3. 确认终态且 worker 不 live 后运行 `collect-query.py`，stdout 是私有日志/状态/前后清单 tar。缺终态时保留 stderr 并报告失败，不将其当成功。

stage、launch、worker 都绑定 fresh `k476-control-delay-r1` handoff、明确授权476/477的总 owner 原件及仅476的 scoped 原件；两 owner 除授权列表/时间外必须一致。检查原 boot guard、363 release/version、handoff 600秒、owner 480秒上限；不会续租。主线持有设备窗和传输，工具不调用 SSH。

worker 比较 APK 数据库、world、repositories、keys 目录/文件/链接及全局 apk.log 的前后名称、字节 hash、类型/owner/mode；所有命令退出码/stdout/stderr留存。只有验签、solver、全局清单不变均通过才标记 passed；`package_transaction_performed` 永远为 false。该结果仍不证明实际安装、升级/回退或完整包事务。

本地 aarch64 缓存 rootfs 的原始 help/version 保存在私有477，help 的正常 exit1 原样保留。最初准备状态与源码/归档哈希见 [preparation-validation.json](preparation-validation.json)。先前“原 query 存在 literal `\\n` 缺陷、主线已修复”的叙述是误读：原 bound stage/launch 的实际 AST 表达式产生 LF，JSON 往返正常，全部 query 哈希仍等于最初准备记录。主线两次本地修复探测在断言前失败，未修改任何 query。公开生成器改用 `chr(10)` 仅使表达更清楚；更正收据见 [json-tail-validation.json](json-tail-validation.json)，错误旧收据保留在私有477。新窗口使用新鲜真实授权和新尝试命名；不得修改旧计划中的时间或 boot 值继续执行。
