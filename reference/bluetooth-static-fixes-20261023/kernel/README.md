# Bluetooth 内核静态问题修复候选

2026-10-23。固定基线 `ba61a62293e0f6bc5838c06f2e85e033e3d702a8`。本目录独立保存候选，旧 PM r2 源码、补丁、测试和软件包保持冻结。未访问手机、SSH、WinRT、射频或 SDK，未链接模块或 Image，未安装/加载。

## 改动

- `candidate/hci_serdev.c`：HCI core 注销结束后，用现有 `proto_lock` 写侧清除 READY/INIT，等待已进入的 RX/send 读侧退出，再永久禁用并等待 UART `write_work`；协议 close、串口关闭后才释放 `hdev`。RX/send 补入同一读侧，发送拒绝保留调用者的 skb 所有权。`init_ready` 等待完成后才取得 hdev，兼容其已关闭协议并将 hdev 置空的失败后置状态。无 `hci_uart` 结构/头文件 ABI 改动。
- serdev flush 同步停用发送工作，处理 `tx_skb`、协议 flush 后恢复工作及积压 wakeup。对应交错：发送工作持有本地 skb，flush 未等待便返回，随后旧工作才把部分发送 skb 发布回 `hu->tx_skb`。新版本先等待发布，再清除该 skb。
- `candidate/hci_qca.c` 保留既有 PM r2 全部改动；WAKE 和 idle SLEEP 的 `GFP_ATOMIC` 分配失败均重挂原定时器，不伪造已发送计数、ACK 或睡眠状态。
- QCA close 先 shutdown 两定时器并 drain 私有工作队列，再最终 purge。对应交错：此前已排队的 awake worker 在旧 purge 后才运行，分配一个 IBS skb；READY 已关闭时发送工作不能替它清队列。新顺序在该 worker 退出后清理。

`kernel-static-fixes-from-r0.patch` 为完整候选补丁；`kernel-static-fixes-from-pm-r2.patch` 为旧 PM r2 的最小增量。两条路径均实际使用 `patch --fuzz=0` 应用并逐字核对完整候选。

## 离线验证

`test-offline.py` 从完整候选及固定原件抽取实际 C 函数，复用冻结 PM 测试中的文字 fixture，绝不 import/执行旧测试生成器。内核锁、定时器和串口 API 使用小型模型；serdev 在途发送/RX 使用 pthread 和显式条件变量控制交错。

- 原 serdev 发送/注销交错：ASan 实际报告 `heap-use-after-free`，日志保留私有。
- 新 serdev 5 例通过：在途发送、在途 RX、partial skb flush、非持久串口、deferred-init 失败后置状态。协议 close 中主动调用晚到 RX/send/TX wakeup，确认拒绝与禁止重新排队。
- 既有 PM r2 的 19 例实际函数回归通过；新增 6 例覆盖一次/连续分配失败、ACK 清重试、idle 最终投票关闭、timer shutdown 不复活、close drain 后 purge。旧 r2 不重挂 WAKE/idle，close 留下 1 个 skb；候选全部修复且分配/释放计数相等。
- 候选 C 通过 ASan/UBSan、`-Wall -Wextra -Werror`；这不是实机或真实内核并发验收。

## 受影响对象编译

仅复用本线既有 `source-view/O`，`-j1 W=1 KCFLAGS=-Werror`，实际编译 `hci_serdev.o` 和 `hci_qca.o`。两个对象外部导入均在原 363 `Module.symvers` 中，同 `hci_uart` 内部导入由原 r2 模块的全局定义核对；未进行新模块链接，不能把对象导入核对称为完整模块链接/加载验证。

首次两个 CC 均 exit 0，但对象符号验证器漏计同模块 `hci_uart_init_work`，随后 generated-header 字节守卫遮盖该错误。`make` 的 SYNC 也把本线此前 BNEP/UHID 事务留下的 generated headers 同步到真实当前 `.config`。已保留首次失败终态、原脚本和日志；修正符号验证后采用已保存的 serdev 对象，仅补编一次 QCA 对象，exit 0、无诊断。

共享源码/构建输入、SDK、旧 PM/GENI/BNEP/UHID 产物不变。本线 `.config`、`Module.symvers`、原源文件/symlink、原两个对象及 `.cmd` 均恢复；本线 generated headers 保留与当前配置一致的同步态，不宣称其相对首次运行前字节不变。

候选对象、完整候选/patch/锁副本及编译/运行日志均位于 `E:/edk2-samurai-out/bluetooth-static-fixes-20261023/kernel/`。公共树仅源码、补丁和脱敏报告。精确来源/候选 hash 见 `source-lock.json`；验证见 `offline-validation.json`、`object-build-validation.json`。下一步由主线统一审查接入，不从本目录自动部署。
