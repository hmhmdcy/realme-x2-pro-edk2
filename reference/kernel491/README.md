# 491：仅更新包的定向复验准备

2026-10-24：按用户要求，相机适配保持暂停，优先完成充电。本轮只整理成果与提交；完整进展、证据边界和恢复步骤见[相机／ISP交接](HANDOFF.md)，不自动申请设备窗口或重启旧事务。

当前仅完成离线准备，尚未绑定设备授权或安装。手机正式版本仍为 r33／r28；[490](../kernel490/README.md) 的 r34／r29 候选只改变 libcamera core，继续复用现有 IPA、签名、代理、441／468 驱动和四份原厂 profile。主摄 720p／1080p 的同帧双遍及固定 FULL／参数、仅改变 PD10 的 LTM 因果实证沿用 [441](../kernel441/README.md)／[442](../kernel442/README.md)，不把本轮工具准备写成新实机结果。

新事务为 native APK 精确七包升级 → 定向采集 → 精确恢复 r33／r28。采集包含四摄 640×480，以及主摄 720p／1080p 的普通／隔离路径，各 12 张；保留实际 bootstrap、数学提交、额外完成与停流取消计数。按 SOF 关联 PD10、WB、已生效 GTM、LTM 参数、IPE 回执及交付图像，要求至少一张成功数学处理实际进入交付。只拒绝本轮修复针对的四类警告，其余警告原样保留。该短段不证明长稳、绝对画质或关闭旧统计积压根因。

双遍还要求 LTM flag 与原厂 `dataCollection` 同时开启。冻结主摄 profile 的两 mode 及匹配 IPA／内核源码已闭合该条件：成功数学帧启用 coarse 数据采集；bootstrap 无 LTM，属于单遍。现有 `m2m_status` 没有 DC／pass 计数，本轮回调只能核同帧消费及成功交付，再结合冻结源／profile 判断双遍 gate；独立的 PD10 扰动因果证明仍引用442原实机结果。

普通路径须实际验签并使用同一应用／IPA 进程；强制隔离按现有 `ipa_manager.cpp` 会在内部验签前返回，因此核对强制日志、独立系统 worker 和同轮普通路径对相同稳定 IPA／签名字节的有效验签。两条路径均核实际 UID10000、CapEff0、pwd HOME、系统库 inode、Manager lease 和停止恢复。无私有库／profile 覆盖。

事务只写包、私有临时目录及原 world／repository 文件的精确恢复，不加载／卸载模块或回写 profile，不创建持久候选仓库，不删除原 r33 仓库。DB 只由原生 APK 恢复，raw DB 仅供取证；恢复全部逻辑条目、文件属性、信任集、原仓库完整成员及已知服务。失败即使恢复成功也保持失败。未知 live 子进程等待同一 Popen 句柄，不杀、不重放；300 秒停止向前，恢复和观察仍须完成。

[准备验收](preparation-validation.json) 已检查实际未绑定归档的 23 文件、权限、全部内容哈希和精确重构的 worker。归档 46,870,927 字节，SHA256 `1e196141bb7066cf79bab14829d6d9168e6f851cc75853653cd8a1a9615b0319`，保存在私有 `kernel491/k491-package-only-r1-offline-template-r1`。未绑定 stage／launch 在目标 I/O 前拒绝。[本地事务检查](local-validation.json) 使用真实本机 Python 子进程和合成事务，未执行真实 APK、服务或手机回调；probe 的有限缓存复核及其缺失证据列于准备验收。

`prepare-runtime.py --attempt r1` 可生成新模板；绑定时同时提供 fresh handoff、总 owner 和 scoped owner。总授权精确为 `[k476-control-delay-r4,k491-package-only-r1]`，scoped 只含前者；fresh476 必须使用私有481 `formal-expected-private.json`。handoff 另绑定 `host_transport.path` 及其 SHA256。`host-run.py` 每次只执行显式的 stage／launch／observe／collect；stage 压缩源码并在目标核 SHA 后编译，原归档仍经 stdin 原字节传输。stage／launch 在发送前落盘单次标记，传输超时保留原输出并仅观察同一窗口。

本轮 callback 只支持 `k491-package-only-r1`；prepare 的其它 attempt 选项不能直接用于设备，需先调整 callback 并重新准备。[传输本地验证](transport-validation.json)与[独立复核](independent-review.json)已通过当前离线范围，真实 SSH 完整 argv 仍须在设备交接后核验。手机由充电任务持有，相机继续零设备访问；必须等用户明确恢复及新 boot／endpoint／guard 与正式基线交回，再按实际差异核对预检，不沿用旧启动身份。尚无本轮安装／恢复证据。原件、包、私有日志和照片保存在外部私有目录，公开副本不含调校或个体数据。
