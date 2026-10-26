# 36. EUD RX：USB 描述符与旧 qcusbser 源码（2026-10-09）

用途：承接 session 35，取得主机路径的新证据，为 USB OUT 对照准备可复现单步工具。
关联：`RX-CONSOLE.md`、`reference/rx36/`、`linux-port/scripts/eud-usb-step.py`。

## 36.1 结论与手机状态

**原生多字节 RX 仍未修复。本轮没有构建或刷写任何镜像，也未修改内核/DTB。**
保留 rx33 的 console、单字符输入和 F1；F1 本轮未触发，不能记为重新验证。
**已完成绕开 qcusbser 的受理成功对照：ABC → 41 90 90，DEFG → 44 90 90 90。**
因此 qcusbser 不是触发该故障的必要条件；仍不能直接确定设备侧根因。

开始时 Windows 枚举：9501 正常；9505 为 COM14，正常；未发现临时终端或抓包进程。
单步发送 `[90][01][03]`（Ctrl-C），第 2 次发送后取得 `tty byte=03` 与 shell 提示符，
确认仍在 Linux。串口由 finally Close/Dispose。

临时终端执行只读命令 `cat /proc/cmdline` 时，已受理 15 个输入字节后，`69` 连续
10 次没有回执，终端停止余下输入并正常关闭。未发换行，命令未完成，不能据此声称
读到了运行中 cmdline。随后独立进程发送 Ctrl-U，首次即取得 `tty byte=15`，清理
了半行命令。没有原样重试该命令，也没有把回执缺失定性为内核崩溃或端口钉死。

源码与已验证镜像仍匹配 session 33：

| 项目 | SHA-256 |
|---|---|
| Windows `linux-port/eud.c` 与 WSL `drivers/tty/serial/eud.c` | 311e5508fccb8d6f0623ba21e7f5891e4fda45984ba9dd6c3a76168037c6d411 |
| `E:\edk2-samurai-out\logdump-rx33-console.img` | d5a36aa2152dd77735f1ea8861f05ad35cb7f714605d5c3cd9db106b6c5f8953 |
| Windows 实装 `qcusbser.sys`，FileVersion/ProductVersion 均为 2.1.3.5 | ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151 |

## 36.2 新的实机 USB 描述符证据

新增 `linux-port/scripts/eud-usb-descriptors.cpp`，使用现有 MSYS2/libusb 读取
描述符；不调用 libusb_open、不 claim、不 reset、不发送 COM 数据。
在现有 qcusbser 绑定下成功执行，证据为 `reference/rx36/rx36-windows-descriptors.txt`。

| 层级 | 实测 |
|---|---|
| 设备 | VID 05c6 / PID 9505，bcdDevice 0100，1 个 configuration |
| 配置 | value 1，总长 **32**，1 个 interface，无 extra |
| 接口 | 0 / alt 0，class/subclass/protocol 均为 ff，2 个 endpoint，无 extra |
| 手机 TX / 主机 IN | **0x81**，bulk，wMaxPacketSize **16** |
| 主机 OUT / 手机 RX | **0x02**，bulk，wMaxPacketSize **16** |

这证明设备描述符的端点/最大包长，不是 USB OUT 抓包。配置长度等于
9 + 9 + 7 + 7，未包含旧 qcusbser 所检查的 MDLM 功能描述符。
ABC 的完整帧只有 5 字节，小于 16；按已审源码的 ZLP 条件，不能用“满包后缺 ZLP”
统一解释此前 ABC 失败。长度 14 的 payload 加头部刚好 16，属于不同边界，不能混淆。

复现（Windows PowerShell；链接参数必须作为一个字符串传给编译器）：

```powershell
$env:PATH = 'E:\msys64\ucrt64\bin;' + $env:PATH
& 'E:\msys64\ucrt64\bin\g++.exe' `
  'E:\RealmeX2Pro edk2\linux-port\scripts\eud-usb-descriptors.cpp' `
  -Wall -Wextra '-lusb-1.0' -o 'E:\eud-host\eud-usb-descriptors.exe'
& 'E:\eud-host\eud-usb-descriptors.exe'
```

## 36.3 旧 WDM 源码补上了哪个缺口

之前只审了新版 WDF 源码。本次找到
[旧 Qualcomm WDM serial 源码镜像](https://github.com/David112x/qualcomm-usb-drivers/tree/ec7480366fc322a7473ec02f6941e8b3e813bbe9/QMI/win/qcwwan/serial)，
固定到 commit `ec7480366fc322a7473ec02f6941e8b3e813bbe9`。
`qcusbser.rc` 标为 **2.1.3.8**；同仓库 installer/ReadMe.txt 列出 2018-12-17 的
**2.1.3.5** 发布记录，之后的记录涉及 PID/架构支持。它更接近已装版本，仍不等于
已装 2.1.3.5 的精确源码，不能据此声称排除了二进制行为差异。

审查结果和可定位行号见 `reference/rx36/source-audit.md`：

* `QCWT.c` 包含 **有条件的 byte-stuffing**，并非所有写请求都无条件原样传递。
  关闭该分支时，原缓冲按 lWriteBufferUnit 分块形成 bulk OUT URB。
* `QCPNP.c` 要求特定 MDLM GUID 和 MDLMD 能力位；`QCUSB.c` 还要求设备响应
  `BTST`，才把 bEnableByteStuffing 打开。本机 32 字节配置没有这些描述符。
  因此，按这份源码的正常路径，不能把 byte-stuffing 当本机已启用的根因。
* `QCMWT.c` 还有聚合、部分完成续传、整包倍数时的 ZLP 路径。没有实装驱动的
  OUT 抓包，仍不能仅凭应用 Write/Flush 的边界代替 USB 传输边界。
* 旧单写路径把 Flush 当排队完成操作；没有看到它作为 RX FIFO advance 命令。
  不再重复 session 33 的去 Flush / 补零实验。

## 36.4 SM8150 握手与时钟：审了具体变更

固定审查 OnePlus SM8150 commit `1dd473abda05a72f6978c47b2a7d80828db6b426`。
RX 函数是 ID → LEN → 连读 DAT，没有另一个逐字节 ACK。IRQ handler 在 RX 分支
后也没有额外的 DAT 完成写入；SAFE_MODE 的 pet 是另一个分支，不能当 RX advance。
SM8150 EUD 节点在 0x88e0000 / 0x2000、IRQ 492，没有 secure-eud 或 clock-vote 属性。

进一步审了三份实际 diff：

* [832b9f6：PHY clock vote](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8150/commit/832b9f6619c849e6ebca0a7a963ac44cdfc1dbba)：
  目的是避免未供时钟的寄存器访问；由 qcom,eud-clock-vote-req 选择使用
  eud_ahb2phy_clk，未改 COM RX 循环。
* [32e5e9d：noirq PM 回调](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8150/commit/32e5e9dc64db59b8d90f748cd98129231eee7572)：
  避免 suspend/resume 与 EUD IRQ 竞争，未改 RX 数据或完成握手。
* [ef3c7d9：QUSB PHY eud_connected](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8150/commit/ef3c7d92895e54245b7d9601ebe49d0696dd16bf)：
  spoof disconnect 时保护 PHY 电源/TCSR，未改 COM 数据接收。

当前上游 `drivers/usb/misc/qcom_eud.c` 仍是角色/PHY 管理，不是 COM tty RX 实现。
搜索没有取得 SM8150 FIFO read-pointer 或 ACK 位的硬件说明。本轮不猜地址写入，
不移植其他 SoC 的 mode-manager/clock 地址；也没有新证据建立量产 COM 单字节限制。
本地 DTS 有 clk_ignore_unused 等参数，但本轮未读到实时 cmdline，不能混为实测。

## 36.5 已完成 USB OUT 对照：绕开 qcusbser 仍失败

现有 Windows usbipd 为 **5.3.0**；WSL 内核为 **6.18.40.1-microsoft-standard-WSL2**。
WSL root 成功 modprobe usbmon，现有 libusb 可用；本轮安装了 usbutils 与 python3-usb。
Windows 未找到已安装的 Wireshark/USBPcap。不能把 usbipd 的 pcapng 功能误认为能
在未转交设备时抓到旧 qcusbser 流量；它记录的是自身转发路径。

初始 9505 为 **6-5 / Not shared**；9501 为 6-1，不共享控制接口。
本进程执行 bind 被系统以需要管理员权限拒绝；用户随后在管理员 PowerShell 完成
`usbipd bind --busid 6-5`，已实查为 Shared。普通权限 attach --wsl Ubuntu 成功，
仅转交 9505，未使用 --force，未改驱动包或安全软件。hrdevmon 警告仍存在，但未阻止
本次正常 attach。WSL lsusb 为 bus 1 / address 2，描述符与 Windows 一致。

新增 `linux-port/scripts/eud-usb-step.py`：仅选单个 05c6:9505，从当前描述符取
bulk IN/OUT，拒绝已有内核驱动占用，不 reset、不 set configuration；一轮仅一帧，
最多 5 次、3 s 间隔，持续排空 TX，收到新回执后停重发并排空 2 s；finally 释放
libusb 资源并关闭 usbmon。保存原始 TX、解码文本、提交/完成事件与目标设备 usbmon。
首次只读排空暴露 usbmon 阻塞 read 导致线程无法 join；finally 已释放 USB，
核实进程 fd 无 /dev/bus/usb 后才终止残留进程。改为非阻塞 read 后，新的只读
排空、Ctrl-U、ABC、DEFG 均正常退出，输出 usbmon_thread_alive=False。
该工具现已完成本轮单步设备验证，仍不是交互终端。

每轮独立进程，开始先排空 3 s；实际均第一次提交就取得新回执，无需重发：

| 捕获前缀 | OUT 提交 / 成功完成 | 手机新回执 | TX 解码 |
|---|---|---|---|
| rx36-usb-ctrlu | 90 01 15，3 / 3 bytes，status 0 | tty byte=15 | 8 帧，0 stray，0 pending |
| rx36-usb-ABC | 90 03 41 42 43，5 / 5 bytes，status 0 | BUFFERED len=3；41 90 90 | 41 帧，0 stray，0 pending |
| rx36-usb-DEFG | 90 04 44 45 46 47，6 / 6 bytes，status 0 | BUFFERED len=4；44 90 90 90 | 50 帧，0 stray，0 pending |

ABC 的目标 usbmon 记录：

```text
ffff8c93b9b569c0 193565402 S Bo:1:002:2 -115 5 = 90034142 43
ffff8c93b9b569c0 193565807 C Bo:1:002:2 0 5 >
```

对应手机在 uptime 5608.985736 报 BUFFERED len=3，随后依次报 byte[1/3]=41、
byte[2/3]=90、byte[3/3]=90。DEFG 也有完整 6 字节提交与成功完成，首字节 44，
后续三个 90。这是同一个 rx33 内核上的新主机路径对照，非旧实验原样重跑。

全部原始 TX、目标 URB、提交/完成/回执事件和配置 metadata 已存 reference/rx36，
SHA-256 在 capture-manifest.json。用法见该目录 README。

USBmon 是 WSL 虚拟主控上的 **URB** 记录，不能称为物理总线抓包，不能独自证明
USB 包边界或物理 ACK，也不能直接证明旧 qcusbser 当时发出了哪些字节。
本轮已经排除了“必须由 qcusbser 才会触发”的解释；仍需考虑共同 USB 栈、初始化
和设备侧访问，不能直接归为熔丝限制。不能把 libusb URB 成功长度等同于已直接观察
硬件内部 FIFO 的全部字节或物理包 ACK。

## 36.6 返回 Windows 与下一步

试验后正常 detach 6-5，9501/9505 均 PNP OK，COM14 能打开并 finally 关闭。
第一次 Windows Ctrl-U 发满 5 次但捕获 0 字节；无受理回执，记为无效样本，
不当作 RX payload 失败，也不声称此时 console 已恢复。所有 USB/串口进程关闭后，
用现有 eudtool 单独 com-off、com-up 一次；新的 Windows Ctrl-U 首次发送即取得
tty byte=15。手机仍为 Linux，串口已关闭；F1 本轮未触发，内核/镜像保持原版。
9505 留在 Shared、没有 Attached；持久共享未删除，后续可再次转交 WSL。

下一步优先查 SM8150 COM 接收完成/读指针推进和初始化、时钟的可定位依据。
USB 短帧的字节内容与成功完成、设备受理现在已有同轮证据；不要再把重装 qcusbser、
去 Flush、补零或同样延时作为首选。需要旧 Windows OUT 抓包时，必须另建其证据，
本轮 WSL 路径不能代替它。改变设备侧读法前提出新的具体依据，并保留 console/F1；
len 3..14 继续仅作诊断，不注入 tty。允许刷写仍仅 boot/logdump。
