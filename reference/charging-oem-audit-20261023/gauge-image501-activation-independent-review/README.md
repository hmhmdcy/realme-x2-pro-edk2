# Image501 activation 独立窄复核

结论：在本次静态审查范围内未发现新增阻断。冻结输入为 `gauge-image501-activation-candidate/delivery.json` SHA-256 `c7983040c0bc5a58976acc4973ea5a2bfd793a62c2a3410cfeb7fb3c0a240a46`。没有运行被审入口、worker、旧测试、设备、SSH、USB、SDK、构建或 Git。

- `guard-fragment.py:72` 绑定本次新事务、已采用的当前 boot guard、精确 k363 version/板型/序号/rootfs、当前完整 boot4126+logdumpACA、R8 manifest/磁盘文件/三模块 note、camera481 和 startup500。候选 boot97811+logdump7e5d 与 Image501 单独固定。`eud_off_check():60` 只读 DT/驱动/tty/console/cmdline，不再通过 CSR/MMIO 控制 EUD。camera wrapper 校验仍检查完整 files/packages/module notes 与 468 note。
- `eud-quiesce.py` 的 `--commit-quiesce` 后硬件序列与原已审 worker 逐字相同，仅工作标签迁移；guard 文本在 quiesce/restart 中一致。`eud-restart.py:135` 先核精确 quiesce 终态和 idle 前提；`--inspect` 在控制操作前退出。`:154` 排他 claim 与文件/父目录 fsync 先于 freeze。`:164` 日志和 BrokenPipe/OSError 不阻断已提交的单次 RESTART2；syscall 返回或抛错则 thaw/close。没有 EUD 解绑、MMIO 或新增硬件控制。
- `controller.py:86` 的真实 SSH Popen 唯一 owner、等待同一 child、PID/startticks/argv 与 terminal 绑定，以及 reconcile/fetch-only unknown 等共 13 个函数，和原已审 host 的 AST 相同。`:235` 新事务还受排他 active-owner、持久 intent 和一次 restart claim 限制。`remote.py` 与原版仅 owner 文件名和事务正则改变。无法确认 child 身份或结果时保留原件、禁止重放；不把未知重启当成功。
- `controller.py:193` 的七份原始 context 导出，独立 AST 比较仅 context schema 字符串变化。dispatch 保留 `syscall_success_proven:false`，不要求在重启后取回已消失的 `/run` 末尾日志。SSH 断开、armed 记录、SSH 真实终态均不证明进入 bootloader 或新系统；现场必须另行取得 fresh fastboot 身份和新 boot 验收。

`review-frozen.py` 仅 read/hash/AST，已实际通过最终字节核对：delivery 全部文件长度与 SHA、原来源 SHA、当前测试收据引用的源码 SHA、13 个保留函数、远端两处 delta、quiesce suffix、嵌入 guard 和 context AST。作者的 4 组定向收据（10 个实际 guard 分支、7 个实际 restart tail 分支、保留流程比较、单 pending prepare）只核绑定并复用，没有重跑或扩大其硬件证明范围。

`context-scope.json` 的 `new_source_sha256=6150…027b2` 是 `read_text()` 换行归一后的 LF 文本 hash；当前 controller 的原 CRLF 文件 hash 是 `bff36…bbf7`。本次独立确认这两个值来自同一最终文件，并绑定作者独立 addendum `0fafcffe54f32d66b8eea91c20a60ad2e3b1ec03fa115b3f08d01555e101860d`。没有将其当作中间源码，也没有修改原 core/delivery/scope。

这份结论仅覆盖上述源码和生命周期增量。载体配对、fastboot 操作器与 postboot 分别由 root/UI 审阅；现场独占、实际重启、刷写和 Image501 运行效果不在本叶证明范围。
