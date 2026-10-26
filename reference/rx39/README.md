# RX39 evidence: tight arrival polling still repeats the first byte

2026-10-09；结论、手动操作和来源审查见 [session 39](../../sessions/39-rx-tight-arrival-poll.md)。
原生多字节 RX 仍未修复。最终为原 rx33-console，Windows COM14 首次 Ctrl-U 有新回执且已关闭。

* `uefi-fast-1.raw/.txt/.events.txt`：新受理 ABC/DEFG；相邻循环入口 625/572 ns，仍 AAA/DDDD，
  随后链式启动原 #44 Linux、tty、shell。13,927 帧、0 stray/pending。
* `uefi-package.log`：原内核/DTB/应用逐字节比对通过，诊断镜像及应用 SHA-256。
* `f1-before-fastpoll.*`：实验前新 F1 回执，另行确认 fastboot。
* `f1-after-fastpoll.*`、`reconnect-clear.*`：Windows OUT 后空抓包，**没有受理证明**。
  与紧轮询之间约有两小时墙钟间隔，不能据此归因。
* `libusb-recover-clear.*`：先 PORT_RESET，再 Ctrl-U 首次受理；同时改变两项，未隔离恢复原因。
* `libusb-f1-after-fastpoll.*`：两次完整 F1 OUT，新 bootloader 回执，随后 errno 5 EIO。
  finally 已释放接口；工具退出 1。另证实 62bc28a1/18d1:d00d fastboot 后才恢复基线。
* `baseline-return-excerpt.txt/.events.txt`：恢复基线后被动抓包的原行号摘录，10,179 帧、
  0 stray/pending、0 OUT。完整原件保存在外部，manifest 留哈希。
* `baseline-native-clear.*`：恢复后 Windows 第一次 Ctrl-U 新回执，停止重发并 Close/Dispose。
  解码文本开头时间戳不完整，不据此宣称完整 TX 无丢帧。
* `windows-final.json`、`usbipd-final.txt`：9501/9505 OK，COM14 关闭，6-5 Shared/未 Attached；基线哈希。

相邻循环入口差不是 USB 到达至 DAT 的端到端延迟。0 stray/pending 只说明重组无需丢弃字节，
不证明完整帧全被捕获。usbmon 为目标 9505 虚拟 HCD URB，不能代替线上 USB 包/ACK 分析。

`.raw`/usbmon 保持原字节；发布解码文本/JSON/log 为 UTF-8/LF、去行末空白副本。
reference/.gitattributes 将 .raw 标记为 binary，避免把串口原始 CR/LF 当文本规范化。
`evidence-manifest.json` 同列外部原件与发布副本的大小和 SHA-256。完整证据在
`E:\edk2-samurai-out\rx39\`，全文硬件头文件在 `E:\edk2-samurai-out\rx39-sources\`。
不把规范文本冒充原始字节；源码下载全文没有纳入 Git。

`source-manifest.json` 给出固定来源、全文 hash 与 GitHub blob 校验值；
`hwio-source-audit.txt` 为原行号索引。目录名 SDM670 的头文件实际声明 SDM845；
SM8250 头文件明确过滤掉 COM RX 字段；SM7150 U-Boot 补丁只跳过 fastboot cleanup。
这些来源没有给出适用 SM8150 的 COM 推进握手，也不足以授权猜地址写入。

当前 [UEFI 探针](../../linux-port/uefi-rx-probe/) 为 RX39 版本；RX38 的 1 ms 版本固定在
703469c。此工具仅用于已经完成的有界比较，不是修复，不再原样重跑。
