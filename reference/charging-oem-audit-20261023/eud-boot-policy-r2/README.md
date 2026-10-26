# Boot-only EUD policy R2：接受本机已观测的完整字

R2 仅将 `SamuraiEudCsrKnown()` 的全字集合从 `0 / 1` 扩展为
`0 / 1 / 0x01010101`。依据是根会话已完成的
`charging-management-20261023/eud-csr-r8-result.json`：同一有效 EUD COM
上下文，两次 32-bit 只读全字均为 `0x01010101`，既有 RX polls 推进，
硬件写入为 0，R8/限值/保护/相机/用户服务与 taint 保持。
[source-evidence.json](source-evidence.json) 固定该收据及执行只读源码的 SHA。

这是对实际见过的 literal 的限定接受，不是 datasheet 的 byte replication、
alias 或寄存器镜像定义。没有按低字节掩码放宽；`0x00010101`、
`0x01000101`、`0x01010100` 等未知全字仍拒绝 arm/当前 Image launch，
callback 遇到未知值也不写。所有成功路径的写入目标仍是**完整 32-bit 0**，
任何非零读回都记录失败。

## 来源支持和边界

固定 Image363 的既有 EUD COM 源 `drivers--tty--serial--eud.c`
（SHA `16670a85…c7bfd`）在 `eud_probe:1345` 向 `CSR_EUD_EN +0x1014`
写 literal1。已有 `eud_reboot_cmd:690–691` 在其停止 RX/IRQ、注销 console、
停止 TX 并持锁的 retirement 流程中写 literal0、读回，随后重启。
两个完整函数的原字节保存在 [existing-eud-functions.inc](existing-eud-functions.inc)。
原 PlatformBm 的固件 BDS 路径也已对同一 32-bit CSR 写1并读取。

这些来源支持保留既有 boot-only 接管中的 literal0 目标，并以新实物全字
证据扩展 arm 接受范围；它们不证明现在 Linux 运行中直接写 CSR 安全。
本轮没有写 CSR，也没有证明硬件已关闭、post-EBS route 已交还、host hub
消失或 SDP500 可被授权。当前观测来自 Linux 已启用 COM 的阶段，不承诺
未来 BeforeEBS 一定读到同一值；未来未知值仍原样拒绝。

## 最小补丁与逐字保留

- [r1-to-r2.patch](r1-to-r2.patch)：相对冻结 R1 的两行小改，只改注释和全字谓词。
- [boot-policy.patch](boot-policy.patch)：相对原 `PlatformBm.c`
  `eda995b4…7198a` 的完整补丁。
- [PlatformBm.c.candidate](PlatformBm.c.candidate)：R2 完整候选，SHA
  `c1ce63b3cc8df1c44b5351f53d15294505df919915fa8773636054305617cee8`。

将 R2 的两行谓词文本还原后，完整源逐字等于冻结 R1
`7cbff9cc…2dab7`。原 panel、其它 cmdline、直接 FIFO 门、arm/callback/disarm
生命周期及所有失败语义均未改变。包括静态 context、单次 Attempted、MapKey
重试不重复写、CloseEvent 失败保持 cancelled、不自动恢复 CSR1，以及 void
BeforeEBS callback 失败不能阻止后续 EBS 的既有边界。

原候选 native DTB 直接复用 SHA
`9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358`，
只复核既有文件 SHA，没有生成/修改 DTB。R1 的 12-case receipt 和独立 FDT
审查收据按 SHA 引用，没有重跑。R1 目录、实装 R8 源码包及其它候选未修改。

## 新增范围验证

[test-result.json](test-result.json) 的 5 个受影响实际 helper/launch 案例，以
ASan/UBSan/`-Werror` 执行真实候选函数，只有 MMIO/BootServices 边界是假对象：
准确 literal 集合、实测字 arm 零写/callback 仅一次写0及精确零读回、近似
unknown 拒绝、callback 变 unknown 零写/不重试、所有非零全字读回失败。
两份补丁另以零 fuzz 在原完整源/R1 完整候选的独立临时副本干跑、应用并
核对输出字节。

本目录未构建 firmware/Image，没有使用 SDK、设备、SSH、USB、共享树或
Git index。它仍是未部署的 boot-only 候选；未来真实 firmware 的全输入/链接
产物绑定、原 Image/DTB/相机 ABI 保留、实体 fastboot 回退路径、callback raw
receipt、postboot 无生产者/CSR0/拓扑与 native 预算检查仍需各自证据。新读数
只补足了“已知实际 CSR 全字”这一项，不能扩大为整机 EUD-off 或 USB500 验收。
