# Session 37：原生多字节 RX 源码搜索与审查

核对日期：2026-10-09。用途：区分可验证的源码差异、旧结论更正与待测假设。
结果：**未找到适用于本机、已有实测支持的多字节 RX 修复。** 本轮不操作串口、不刷机。
过程与下一步见 [session 37](../../sessions/37-rx-source-search-and-phy-lifecycle.md)。

## 1. 同机型和新厂商源码没有补出 RX 握手

Realme X2 Pro 官方源码固定到 `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6`：

* [eud.c:418](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/soc/qcom/eud.c#L418)：读 ID、读 LEN、连续读 DAT，无逐字节 ACK。
* ID/LEN 没有 mask。按本机复制到四个 lane 的读值，ID 比较不能通过，LEN 也不能照搬。
* [eud.c:631](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/soc/qcom/eud.c#L631)：`uart_add_one_port()` 后为 `if (!ret)`，成功反而跳到 error，未设置 eud_ready，也不进入后面的 enable。
* [sm8150.dtsi:1645](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/qcom/sm8150.dtsi#L1645)：0x88e0000/0x2000、SPI 492；没有 secure-eud / clock-vote 属性。

这些问题说明原厂公开代码不能直接视为本机多字节成功的参考实现，**不证明原厂从未测试**。
当前自有驱动已有 ID/LEN mask 和正确的 `if (ret)`；修这些旧代码问题不能解释现有故障。

进一步查到 [OnePlus SM8850 eud.c:560](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8850/blob/fc30e54174d254ff7f33622a9278e4435f6718d2/drivers/soc/qcom/eud.c#L560)：RX 仍相同，无新 advance。
其 `uart_add_one_port` 判断已正确，但 ID/LEN 仍未 mask；新增的 secure/TCSR/UTMI 配置属于其他 SoC，不能写进 SM8150。
全局 `COM_RX_DAT` 搜索取得的多份厂商结果也是该循环；搜索结果有索引和数量限制，不作穷尽性断言。

## 2. 更正 QUIC WriteCommand 的重载归属

固定 QUIC 源码 `693741a3b0448690402539ed0e6af067510e386f`，逐个核对声明和调用：

| 位置 | 实际行为 |
|---|---|
| [eud.cpp:866](https://github.com/quic/eud/blob/693741a3b0448690402539ed0e6af067510e386f/src/eud.cpp#L866) | 三参数 `(opcode, uint8_t *data, uint8_t *rvalue)` 从缓冲首字节 memcpy，确有覆盖 opcode 的错误。 |
| [eud.cpp:1131](https://github.com/quic/eud/blob/693741a3b0448690402539ed0e6af067510e386f/src/eud.cpp#L1131) | 两参数 `(opcode, uint8_t *data)` 使用 `data_out_p + 1`，保留 opcode。 |
| [com_api.cpp:169](https://github.com/quic/eud/blob/693741a3b0448690402539ed0e6af067510e386f/src/com_api.cpp#L169) | TX/RX timeout 使用两参数版本。session 33 曾把它归到错误重载，本轮更正。 |

本项目原始帧不经错误重载；**修改 memcpy 既不是本机 RX 修复，也不修复 COM timeout 调用**。
公开 COM 原型的 ID/LEN/DAT 注释与下游一致，没有提供额外 FIFO 完成握手。
[官方 issue #6](https://github.com/quic/eud/issues/6) 是 session 33 已见线索，本轮复核时仍 open，仅有 stale bot 评论，没有维护者给出 COM 实现/修复。不能把询问者陈述当厂商结论。

## 3. 最新 PHY 补丁提供的是初始化线索

追到 Elson Serrao 的 [v9 系列，2026-09-29](https://patchew.org/linux/20260929213513.2401005-1-elson.serrao@oss.qualcomm.com/)。
下载完整 8 封 patch mbox，解码 quoted-printable 后审查；全系列没有 COM_RX、COM_TX、tty、uart、FIFO 匹配。
它的验证是其他平台 OpenOCD 连接，不是 SM8150 多字节 COM。

* [3/8：PHY 管理](https://patchew.org/linux/20260929213513.2401005-1-elson.serrao@oss.qualcomm.com/20260929213513.2401005-4-elson.serrao@oss.qualcomm.com/) 明确指出旧单路径实现依赖 USB 控制器初始化 PHY，添加 EUD 自身的 phy_init / phy_power_on。
* [6/8：角色管理](https://patchew.org/linux/20260929213513.2401005-1-elson.serrao@oss.qualcomm.com/20260929213513.2401005-7-elson.serrao@oss.qualcomm.com/) 处理 device role 下的使能和同步。
* [7/8：虚拟插拔](https://patchew.org/linux/20260929213513.2401005-1-elson.serrao@oss.qualcomm.com/20260929213513.2401005-8-elson.serrao@oss.qualcomm.com/) 把虚拟 detach 的 HOST 改成 NONE；不是 DAT advance。

本地静态核对：现有 eud.c 的 probe 仅写 CSR_EUD_EN，无 PHY 获取/供电管理；实际 WSL DTS 的 COM 节点只有 reg/status。
MTP 包含 USB HS/QMP PHY enabled 和 peripheral DWC3，**不能说整个 USB 在 DT 中被禁用**。
固件源码和实际 WSL DTS 均有 clk_ignore_unused / pd_ignore_unused / regulator_ignore_unused；这只是静态配置，本轮没有取得手机运行时 cmdline 或 PHY 状态。

已有 rx33 恢复版启动记录 `rx33-final-i.txt` 包含：88e8000.phy 等待 ldo5、a600000.usb 的 dwc3 初始化延迟，以及 88e2000.phy 的 sync_state pending。
这使 PHY 生命周期成为有依据的排查方向，但记录发生于启动约 26 秒，**不证明它始终失败或当前仍失败**。
88e8000 的 QMP 供应者问题也不能直接当作 88e2000 HS PHY 的错误原因。
摘录与原文件 SHA-256 见 `local-evidence-manifest.json`；原始完整文件仍在 E:\edk2-samurai-out。

session 38 更正：本机 SM8150 HS PHY 实际匹配 `phy-qcom-snps-femto-v2.c`，不是这里曾参考的 QUSB2。
实际 SNPS init 同样开启供电/时钟并 assert/deassert reset，因此直接 phy_init 的接管风险仍需审查。
这条具体匹配依据与新的启动/UEFI 对照见 `sessions/38-rx-pre-linux-and-usb-boundaries.md`；
session 37 尚未证明安全接管，未移植 v9，也未猜时钟/TCSR 地址或重刷。

## 4. 启动源码搜索的边界

BOOT.XF.3.3 的 [EudLib.c](https://github.com/SwedMlite/BOOT.XF.3.3/blob/55ff7c1920ccf084951b2770d46ffcbe8917864f/QcomPkg/Library/EudLib/EudLib.c) 中 Eud_Read 读取的是 enable 状态，不能当 COM payload 读取实现；该树目标是 SM8250。
较新 BOOT.MXF 树的 EUD.h 是早期使能 API，EudTargetLibNull 是配置桩；没有找到 SM8150 的 read-pointer/ACK 定义。
Casey Connolly 的 [2025-06-30 原文](https://www.linaro.org/blog/hidden-jtag-qualcomm-snapdragon-usb/) 明确区分已测试的 SWD 和尚未探索的 COM/trace。
公开 SWD 的批处理、STATUS/FLUSH 命令不能类推成 COM 握手。
EUD 专利只给架构和低功耗供电/时钟概念，没有 COM FIFO 寄存器规范。

## 5. 证据保存

`source-manifest.json` 固定仓库、commit、Git blob、文件大小与 SHA-256。8 个完整 Git 文件核对 blob 一致；另有明确标注的 DTS 行摘录和原始 patch mbox。
外部完整代码保存在 `E:\edk2-samurai-out\rx37-sources\`，不复制进发布仓库。
`local-lifecycle-audit.txt` 是静态审查输出；`rx33-final-i-usb-excerpt.txt` 保留原行字节，仅作历史证据。
Windows 枚举发布副本规范为 UTF-8/LF；原始输出保存在外部 sources 目录，原始和规范副本哈希均已记录。
