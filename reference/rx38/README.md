# RX38 evidence: pre-Linux comparison and USB boundaries

2026-10-09；完整结论和操作范围见 [session 38](../../sessions/38-rx-pre-linux-and-usb-boundaries.md)。
原生多字节 RX 仍未修复。当前设备已恢复 rx33-console 基线，Windows COM14 Ctrl-U 有新回执并已关闭。

## 1. 实机证据

* `uefi-1.raw/.txt/.events.txt`：最小 UEFI 应用在 Linux 运行之前受理 ABC/DEFG，连读为 AAA/DDDD。
  原始回读字为 41414141 / 44444444；日志在整帧缓存之后输出。
  随后原内核、tty 和 shell 启动；13,917 重组帧、0 stray/pending。
* `f1-before-uefi.*`、`f1-after-uefi.*`：两次新 bootloader 回执，均另确认 62bc28a1 fastboot。
* `uefi-package.log`：原内核、DTB 逐字节比较通过，诊断镜像和 EFI 应用哈希。
* `before-setup-ABC.*`、`port-reset-ABC.*`：完整 OUT 及新回执，reset 后仍 41 90 90。
* `rx-timeout-DEFG.*`：完整 OUT、无设备回执；不能当受理后的 payload 反例。
  `reset-after-rxto.*` 有新的 Ctrl-U 受理。
* `full16-nozlp.*`、`full16-zlp.*`：合法 LEN=14、16 字节 OUT，后者另送 0 字节 OUT。
  新回执分别为 41/61 后 13 个 90，没有改善。
* `baseline-return-excerpt.txt`：恢复基线后被动启动抓包的带原行号摘录，0 OUT；完整原文件在外部。
* `windows-return-clear.*`：detach 回 Windows 后 Ctrl-U 首次受理。

`.usbmon` 仅捕获目标 9505 的虚拟 HCD URB，不能代替物理 USB 包和 ACK 分析。
0 stray/pending 只表明重组无需丢弃字节，不证明所有完整 TX 帧都被捕获。
COM timeout/reset 设置没有协议读回；USB 完成不能证明设置生效。

`evidence-manifest.json` 列出外部完整证据的大小、SHA-256 和是否发布同名原文件。
`.raw`/usbmon 保持原字节；发布的解码文本和 JSON 为 UTF-8/LF、去行末空白的规范副本。
manifest 同时保留外部原件与发布副本的大小/哈希，不能将规范文本冒充原始字节。
所有外部文件在 `E:\edk2-samurai-out\rx38\`；构建日志、反汇编、基线全启动日志等仅留哈希和本地原件。

## 2. 源码依据与边界

本轮外部全文在 `E:\edk2-samurai-out\rx38-sources\`，固定链接、大小、SHA-256 和计算的 Git blob
见 `source-manifest.json`。Linux 两份文件另通过 GitHub fetch 的 blob SHA 核对一致。
本地内核 HEAD e42788e 是自有提交，**源文件链接使用真正上游基线 a90ee4305c4a5df72c11b31dacfdc76e00fcf78a**。

| 固定来源 | 本轮审查结论 |
|---|---|
| [Linux sm8150.dtsi:3455](https://github.com/torvalds/linux/blob/a90ee4305c4a5df72c11b31dacfdc76e00fcf78a/arch/arm64/boot/dts/qcom/sm8150.dtsi#L3455) | HS PHY 为 qcom,sm8150-usb-hs-phy；只提供 ref 时钟。 |
| [SNPS femto-v2:154](https://github.com/torvalds/linux/blob/a90ee4305c4a5df72c11b31dacfdc76e00fcf78a/drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c#L154) | cfg_ahb optional；init:386 会开供电/时钟、reset、POR/UTMI override；match:499 匹配 SM8150。纠正 session 37 的 QUSB2 参考归属。 |
| [Realme dwc3-msm.c:3651](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/usb/dwc3/dwc3-msm.c#L3651) | 有条件配置 AHB2PHY TOP_CFG=0x11，依赖 ahb2phy_base 和 cfg_ahb 时钟；不能无资源照搬。 |
| [Realme sm8150-usb.dtsi:19](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/qcom/sm8150-usb.dtsi#L19) | primary/secondary USB 均无 ahb2phy_base/cfg_ahb；HS 节点同为 SNPS femto、ref_clk_src。 |
| [Realme gcc-sm8150.c](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/clk/qcom/gcc-sm8150.c#L4162) | 搜索未见对应 cfg AHB2PHY clock 定义；仅 reset ID 不能作为可用 clock。 |
| [TestEUD port_test.cpp](https://github.com/sunflower2333/TestEUD/blob/6b87340ec46c8147acb50cfb3c456a41352c9dc4/port_test.cpp) | 主机测试沿用 QUIC 注释，无设备侧 DAT advance 或成功日志；不能视作已验证对照。 |

`phy-source-audit.txt` 保留本地原行号。没有将上述线索改为寄存器写入或移植 PHY 系列。
COM opcode/timeout 示例的固定 QUIC 来源已在 session 37 和各实验 `.json` 中记录。

## 3. 复现工具

`../../linux-port/uefi-rx-probe/` 是独立、最多两次 25 秒等待的 UEFI 对照应用和手动打包/抓包工具，
实验后链式启动原内核；它不是修复，也未替代发行的 boot 固件。
`eud-usb-step.py` 新增 `--setup`、`--read-size 16`、满包后的 `--zlp`；每一步均有上限和 finally 释放。
