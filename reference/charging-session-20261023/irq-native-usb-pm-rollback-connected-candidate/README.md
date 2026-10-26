# 当前 USB PM 两文件冷回退：连接式执行

2026-10-24。接通[当前原动作/probe/binder](../irq-native-usb-pm-rollback-host-candidate/README.md)与[当前设备执行器](../irq-native-usb-pm-cold-rollback-candidate/README.md)。仅离线完成，未生成实际手机事务、lease、SSH、回退或重启。

## 接线

复用原 `rollback-connected-candidate` 的同 child 监督。十一项主机函数逐字保持：文件持久化、原进程身份、SSH owner、有限父等待、原终态审核与原 launch 传输审核。remote 只换事务前缀、当前请求 schema 和固定6818939b worker；supervisor 只换请求 schema。原 regular request fd、真正 EOF/原子进程 wait、日志释放、35秒父等待返回 pending、未知结果只 status/fetch 均保持，没有新增进程执行框架。

新增或改变的入口：

- `probe` 先审核实际 source/选定动作，再创建固定私有输出。使用原 `irq-postboot-compressed-profile.send_readonly` 与原严格密钥，固定 `-C`；与当前 binder 期待 argv 逐项相等才发送。输出名为 `probe-[a-z0-9-]{8,48}`，只能位于本 host 的 PRIVATE 下。失败保留原输出，不能对同目录重试；新只读 probe 不会写 lease 或停止充电。
- `bind` 调用当前 binder；`bound(..., launching=True)` 重审来源、所选实际动作与原当前 probe。除身份、source stage和activation外，增加 source帧进程观测与current cache的逐项一致性，避免请求中的这两项脱离原审核结果。
- `launch/status/fetch` 沿原 transport，唯一参数变化为固定 `-C`。当前 request和同6818源码逐字交给监督器；当前boot/身份不一致时不能launch。事务已存在、部分或unknown时只查询/取回原件，不换事务盲目再执行。
- `fetch` 使用实际当前profile的 notes字典与两文件集合，核对真实原进程链、wait与final_files。写回7cb/18e8仅是 `staged_original/runtime_pending`，始终 `runtime_validation_accepted=false`；不能把两文件成功视为ace2/旧模块已经运行。

默认运行 `host.py`、`remote.py`、`supervisor.py` 均不接触手机。实际入口仍需明确当前独占窗口；当前相机用户暂停/归档的状态不由此工具改变。

## 定向验证

七组当前差异检查通过，三个默认入口通过；原本地child均实际wait0：

1. 十一项owner函数逐字相等、remote只三项替换、固定压缩argv与原profile一致。
2. 实际binder/probe原回执重审；篡改current cache或source进程观测即拒绝launch。
3. 三驻留分支的remote精确request/源码、唯一launch、120秒lease及跨boot只取回旧PID证据。
4. 实际6818 worker在设备IO模型中产生的两文件结果，经过真实fetch审核；错误驻留notes拒绝，成功仍runtime_pending。
5. 实际transfer固定压缩、未确认窗口无intent、pending不可重复launch；原launch wait不明时不提升成功。
6. 当前probe接原只读接口、缺source不提前建目录、失败输出保留、同目录不重试。
7. 当前schema经原supervisor，用regular request fd传递完整请求、同一worker wait及终态持久化。

只在设备/传输IO和原source审核边界建模，没有实际SSH/USB。旧29项owner/wire和3项transfer矩阵按未变函数复用，不重跑旧矩阵；不冒认当前真实回退。首派生时路径匹配失败在emit前拒绝，已保存 `history/prepare-attempt-1/`；修正匹配及替换顺序后生成与本地检查通过。

## 剩余

尚需接齐恢复后的硬件收拢、ace2单载体/正常重启与新boot核验，并更新当前504组合的postboot/adoption。齐备后才安排一次串行实机窗口，核对当时真实手机状态，不能沿用旧离线身份。

当前最近确认的手机仍502/edd/ace2、7cb/97c/7848/18e8；本叶没有改变桌面、相机、保护缓存、充电额度或任何手机分区。
