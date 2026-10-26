# Session 36 源码审查定位（2026-10-09）

用途：把主机写路径与 SM8150 RX 握手结论固定到具体源码，便于下一轮复核。
关联：`../../sessions/36-rx-usb-descriptors-and-legacy-qcusbser.md`。
源文件下载在 `E:\edk2-samurai-out\rx36-sources\`；不把完整外部代码或驱动二进制复制进仓库。
`source-manifest.json` 保存文件大小、SHA-256、固定 commit 的原始 URL。

## 旧 WDM qcusbser：实际审过的分支

仓库镜像 commit：`ec7480366fc322a7473ec02f6941e8b3e813bbe9`。
代码自带 Qualcomm 版权；此镜像不是实装驱动供应包的官方可复现构建。

| 文件 / 行号 | 观测与边界 |
|---|---|
| [qcusbser.rc:53](https://github.com/David112x/qualcomm-usb-drivers/blob/ec7480366fc322a7473ec02f6941e8b3e813bbe9/QMI/win/qcwwan/serial/qcusbser.rc#L53) | FILEVERSION / PRODUCTVERSION 为 2.1.3.8；实装是 2.1.3.5，不能视为完全相同源码。 |
| [installer/ReadMe.txt:73](https://github.com/David112x/qualcomm-usb-drivers/blob/ec7480366fc322a7473ec02f6941e8b3e813bbe9/QMI/win/qcwwan/installer/ReadMe.txt#L73) | 1.00.57 / 2018-12-17 列出 serial 2.1.3.5；文首最新发布列 2.1.3.8。只建立版本谱系。 |
| [QCWT.c:1031](https://github.com/David112x/qualcomm-usb-drivers/blob/ec7480366fc322a7473ec02f6941e8b3e813bbe9/QMI/win/qcwwan/serial/QCWT.c#L1031) | IRP_MJ_FLUSH_BUFFERS 走队列完成路径；没有发现其作为设备 RX advance 的额外命令。 |
| [QCWT.c:1083](https://github.com/David112x/qualcomm-usb-drivers/blob/ec7480366fc322a7473ec02f6941e8b3e813bbe9/QMI/win/qcwwan/serial/QCWT.c#L1083) | bEnableByteStuffing 为真时才构造填充缓冲；不能无条件宣称整个旧驱动原样传递。 |
| [QCWT.c:1147](https://github.com/David112x/qualcomm-usb-drivers/blob/ec7480366fc322a7473ec02f6941e8b3e813bbe9/QMI/win/qcwwan/serial/QCWT.c#L1147) | 正常分支 pActiveBuffer=pBufferToDevice，ulActiveBytes=ulBTDBytes；1152 按 lWriteBufferUnit 截取，1162 建立 bulk URB。 |
| [QCPNP.c:2048](https://github.com/David112x/qualcomm-usb-drivers/blob/ec7480366fc322a7473ec02f6941e8b3e813bbe9/QMI/win/qcwwan/serial/QCPNP.c#L2048) | MDLM GUID 必须匹配 98b06a49-b09e-4896-9446-d99a28ca4e5d；MDLMD 对应能力位才开 byte-stuffing/padding，2137 无 vendor feature 则清除能力。 |
| [QCUSB.c:1431](https://github.com/David112x/qualcomm-usb-drivers/blob/ec7480366fc322a7473ec02f6941e8b3e813bbe9/QMI/win/qcwwan/serial/QCUSB.c#L1431) | 无 bByteStuffingFeature 直接返回；请求 0x0e/0x0f，设备返回四字节 BTST 才更新 bEnableByteStuffing。 |
| [QCMWT.c:226](https://github.com/David112x/qualcomm-usb-drivers/blob/ec7480366fc322a7473ec02f6941e8b3e813bbe9/QMI/win/qcwwan/serial/QCMWT.c#L226) | 已发送正数且为 wMaxPktSize 整数倍时，队列空闲路径可追加 ZLP；不解释 5 字节 ABC 的一般失败。 |
| [QCMWT.c:603](https://github.com/David112x/qualcomm-usb-drivers/blob/ec7480366fc322a7473ec02f6941e8b3e813bbe9/QMI/win/qcwwan/serial/QCMWT.c#L603) | 聚合分支与普通缓冲/部分完成续传并存；680 建立 bulk URB。应用一次 Write 不能直接证明总线提交边界。 |

本机配置是 9+9+7+7=32 字节，无上述 MDLM/MDLMD extras。**按这份源码的正常
能力探测路径**，byte-stuffing 不应启用；这是有条件推论，尚非实装二进制 OUT 证据。
不据此替换驱动、写注册表或再次重复补零/去 Flush 实验。

新版官方 WDF 对照仍固定到已审本地树
[`a42c05276c1aa45eab231760502665c8ccef6b14` / QCWT.c](https://github.com/qualcomm/qcom-usb-kernel-drivers/blob/a42c05276c1aa45eab231760502665c8ccef6b14/src/windows/wdfserial/QCWT.c)。
它的普通写路径格式化原 WDF memory，整包倍数条件下处理 ZLP；不等于 2018 年驱动。

## 同 SoC 下游与实际变更

OnePlus SM8150 源树固定到 `1dd473abda05a72f6978c47b2a7d80828db6b426`。

| 文件 / 行号 | 观测 |
|---|---|
| [eud.c:418](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8150/blob/1dd473abda05a72f6978c47b2a7d80828db6b426/drivers/soc/qcom/eud.c#L418) | RX 先读 ID，过滤 UART_ID 0x90，读 LEN，再连续读 DAT；没有逐字节 ACK。原函数还不 mask ID，不能无条件照搬。 |
| [eud.c:477](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8150/blob/1dd473abda05a72f6978c47b2a7d80828db6b426/drivers/soc/qcom/eud.c#L477) | RX IRQ 分支后没有另一个完成写入；SAFE_MODE 的 pet 属于独立分支。 |
| [eud.c:593](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8150/blob/1dd473abda05a72f6978c47b2a7d80828db6b426/drivers/soc/qcom/eud.c#L593) | qcom,eud-clock-vote-req 才取 eud_ahb2phy_clk 并 vote；不是所有 SoC 通用的必需配置。 |
| [sm8150.dtsi:1645](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8150/blob/1dd473abda05a72f6978c47b2a7d80828db6b426/arch/arm64/boot/dts/qcom/sm8150.dtsi#L1645) | EUD reg 0x88e0000 / size 0x2000，GIC SPI 492，节点未含 secure-eud 或 clock-vote。 |

已打开并审查实际 diff：

* [832b9f6619c8](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8150/commit/832b9f6619c849e6ebca0a7a963ac44cdfc1dbba)：添加可选 PHY clock vote，避免 unclocked 寄存器访问，未改 RX 循环。
* [32e5e9dc64db](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8150/commit/32e5e9dc64db59b8d90f748cd98129231eee7572)：改用 noirq PM 回调，避免 IRQ 竞争，未改 RX 完成。
* [ef3c7d92895e](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8150/commit/ef3c7d92895e54245b7d9601ebe49d0696dd16bf)：QUSB PHY 的 eud_connected 电源/TCSR 保护，未改 COM FIFO。

审查范围内没有取得 SM8150 COM FIFO read-pointer / ACK 硬件文档。这不证明硬件
没有额外要求，更不证明量产熔丝限制了多字节 COM。不盲写未知位或其他 SoC 的时钟地址。
本轮已完成同内核 libusb/WSL 对照，受理的 ABC/DEFG 仍失败，详见 session 36.5；qcusbser
不是触发条件的必要部分，下一步应继续设备侧或共同路径的具体依据。

## USB 路径的工具文档

[usbipd WSL support](https://github.com/dorssel/usbipd-win/wiki/WSL-support) 说明
bind 需要管理员、attach/detach 的用法；
[Troubleshooting](https://github.com/dorssel/usbipd-win/wiki/Troubleshooting)
用于确认过滤器和 usbipd 自身抓包的边界。本进程 bind 被拒绝后，用户已完成管理员
bind；正常 attach 成功，实验后 detach。usbmon 提供 WSL 虚拟主控 URB，不能代替
旧 qcusbser 的抓包或物理 ACK。
