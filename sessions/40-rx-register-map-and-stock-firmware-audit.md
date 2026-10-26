# 40. 完整寄存器表与原厂 SM8150 固件审查（2026-10-09）

**原生多字节 RX 仍未修复。** 本轮只搜索、静态审查和检查基线单字节回执；没有重跑 ABC/DEFG，
没有修改或刷入 boot/logdump、Linux、DTB、PHY/时钟寄存器。session 39 的 AAA/DDDD 仍是最新多字节实测。

## 40.1 新找到的完整 EUD_ACORE 表

此前 USB 专用 HWIO 头文件省略了 COM；继续审查同一公开固件树的 DSP 调试器表，
找到 [SDM845 hwioreg.per](https://github.com/Rivko/android-firmware-qti-sdm670/blob/20bb8ae36c93fc16bbadda0e0a83f930c0c8a271/adsp_proc/core/systemdrivers/hwio/scripts/sdm845/hwioreg.per)。
全文 62,617,319 字节，Git blob `745c7cb71ecaaab995b989982fe94713a3b32e3d` 已校验。
初次下载截短，补取经过 Content-Range 校验的尾段后才审查；未把截短文件当完整证据。

该表的 EUD_ACORE 位于 0x088e0000，COM TX/RX 与既有布局一致，字段都是低 8 位。
RX ID/LEN/DATA 和 INT_STATUS_0/1 标为 Read；另有 FLAG_IN_WR/SET/CLR、FLAG_OUT、CTL 和版本寄存器。
**它没有描述 DAT 的读副作用、RX 完成握手、flag 各位意义或 EE ID 路由。**
因此不能把 flag 清除或 INT_STATUS 写入当新修法，也不能从“未列出”推出没有隐含握手。
这是 SDM845 表，不是 SM8150 的可移植编程手册；其 TOP_CFG=0x088ee010 也没有建立本机写入依据。
最小寄存器索引和全文哈希见 reference/rx40；全文只留在外部输出目录。

## 40.2 X2 Pro 原厂 SM8150 二进制

取得 Project-Aloha 的 RMX1931 `BOOT.XF.3.0-00501-SM8150LZB-1`：
[HWIODxe](https://github.com/Project-Aloha/binaries_extracted/tree/adf853e45436bfcfd4274fa5d51b921c8b66e9f2/sm8150/realme/rmx1931/BOOT.XF.3.0-00501-SM8150LZB-1/QcomPkg/Drivers/HWIODxe)、
[UsbConfigDxe](https://github.com/Project-Aloha/binaries_extracted/tree/adf853e45436bfcfd4274fa5d51b921c8b66e9f2/sm8150/realme/rmx1931/BOOT.XF.3.0-00501-SM8150LZB-1/QcomPkg/Drivers/UsbConfigDxe)。
两者均与 Git blob SHA 校验一致，内嵌构建路径包含 SM8150、19781 和 SDM855LA_Core。
只解析 PE 和反汇编，没有执行下载的固件或替换当前工作 blob。

UsbConfigDxe RVA 0xf174 的小函数读取 0x088e1014、返回 bit 0，并引用 `usb_eud_is_active` 字符串。
RVA 0x753c/0x78c0 的调用路径在 EUD 活跃时跳过对 0x00112000 的一段操作；
本地 gcc-sm8150.c 将 GCC_QUSB2PHY_PRIM_BCR 列为 GCC +0x12000。
这给出了该机型保留 EUD PHY 状态的静态依据，**没有给出 COM RX advance 修复**。
另一处直接访问 0x088e1018 用于 attach 切换；没有据此触发 detach/reset。

本次直接地址/调用点审查未取得 COM RX 实现或 AHB2PHY wait-state 设置。
literal 搜索缺失不排除间接地址访问，也没有全面反编译所有固件模块，不能声称排除了整个原厂固件。

## 40.3 参考实现的证据边界

再读 [QUIC com_api.cpp](https://github.com/quic/eud/blob/693741a3b0448690402539ed0e6af067510e386f/src/com_api.cpp)：
示例 test_function 中真实 USB 收发仍在 FIXME 注释块内；EE enable/TX_ID 的说法也仅在注释里。
不能当成功测试，不能据此猜 TX_ID bitmask。session 31 的 0x81/82/83 失败也不是新候选。
quic/eud issue 6 最新评论只是 stale 提示，没有修复回复。本轮未发现新的已验证同 SoC 成功对照。

仍缺少能决定下一步的证据：SM8150 COM RX 读副作用/完成握手规格，或可复现的同 SoC 原生成功实现。
libusb/WSL 已排除 qcusbser 是必要触发因素，但 usbmon 只证明虚拟 HCD 的 URB，不能代替物理总线采样。
当前主机没有发现 USBPcap 服务/程序；没有安装过滤器、force bind 或改 hrdevmon。

## 40.4 最新设备核对

9501/9500/9505 均枚举 OK，COM14、6-5 Shared/未 Attached。
有界 Windows 单步发送 `[90 01 15]`：第 2 次 OUT 后取得新 `eud: tty byte=15` 回执并停止重发；
finally 已 Close/Dispose COM14。原始 42 字节解出 7 帧、0 stray，时间戳前缀截断，不能当完整 uptime 或无丢帧证明。
这只验证当前单字节/tty 路径可响应，不是多字节成功，也没有本轮重新触发 F1。

当前镜像仍是 session 39 恢复的 rx33-console。内核已有修改及备份文件保留，仓库此前干净。
完整外部审查文件：`E:\edk2-samurai-out\rx40-sources\`；本轮回执：`E:\edk2-samurai-out\rx40\`。
公开最小证据：reference/rx40。下一步继续以真实 ABC/DEFG 完整 payload 为成功标准，
没有新依据时不重跑轮询/延时/满包/ZLP/reset 组合。
