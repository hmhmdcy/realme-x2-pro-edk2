# 43. 原生终端输出证据更正与缺回执边界（2026-10-09）

用途：复核 RX41/42 的缺输出判断，审查 USB OUT→RX→tty/BusyBox→TX，
并在保留 TOP_CFG=0x11 整帧修复的基线上做有界对照。
来源：未改动的 reference/rx41 原始抓取、本轮 [reference/rx43](../reference/rx43/README.md)、
实际 WSL 内核/工作 initramfs 与同版本 BusyBox 官方源码。

## 43.1 主要结论

**之前数次“缺命令输出”是证据查看错误，撤回这些样本的故障判断。**
`decode-eud-capture.py` 原来只在 stdout 打印含 `eud:` 的行，完整响应一直在
原始 `.raw` 和解码 `.txt` 里。RX41 原始哈希全部通过，没有改写原始文件。

| RX41 原始抓取 | 实际完整响应 |
|---|---|
| native-id、native-id-cr、bulk-native-id、ordered-native-id | uid=0 gid=0，加提示符 |
| native-echo-14 | RX41-TTY，加提示符 |
| ordered-console-native-suffix | RX41-C，加提示符 |

RX41 前后候选均有响应，所以不能把 ordered 的先回执后 tty 改动称为输出修复。
对应文档已更正，reference/rx41/verify.py 增加这些响应的原始数据断言。
原生 payload 修复是真实整帧读数，本轮保留它；兼容终端也保留逐字模式。

**偶发缺回执仍可复现，且 qcusbser 不是必要条件。** 新 Windows echo A 的三次
OUT 没捕获回执，之后取得的新 dmesg tail 中也没有该 payload 的设备 RX 记录；
前后 Ctrl-U 与后续 echo B 记录均存在。该轮问题范围缩小到驱动完整帧记录之前，
不是仅把 tty 响应隐藏了。仍无法区分 USB/EUD 未交付、STATUS1 未被轮询观察到、
无效头部被拒等情况；没有物理 USB 总线 ACK、IRQ 或空闲头部的实测。

## 43.2 实时起点与改动边界

首先读 HANDOVER-NEXT、RX-CONSOLE、FLYWHEEL 与 sessions 41/42。
实时设备实际是 Android Bootloader Interface，62bc28a1，usbipd 当时显示 4-4；
不是上一轮 Linux/COM14 快照。指定序列号的有界 getvar product 返回 msmnile。
未发现其他相关串口进程；随后独占打开成功，每次结束都 finally Close/Dispose。

WSL EDK2 仓库起点 cf87864，干净；内核已有 DTS、rpmh.c、eud.c、earlycon 的
工作树修改与备份均保留。核对 RX41 候选镜像、当前 Image、eud.c、实际 init
的 SHA256 均与 session 41 一致。启动日志也是该驱动、#48 内核和 TOP_CFG=0x11。
没有读取设备 logdump 分区来计算整分区哈希。

本轮没有修改内核、DTB、initramfs、固件或构建/刷分区。只用 fastboot reboot
启动现有内容；F1 后仍重启同一候选。未执行旧 build-image.sh，没有 PHY/时钟
reset、force bind、驱动/过滤器变更，也没有设置 COM timeout 或发 PORT_RESET/ZLP。
USB 对照只 attach 已 Shared 的 6-5，资源释放后单独 detach。

## 43.3 小步实测与证据分层

每轮使用新文件名，完整原生帧，最多三次 OUT，取得新回执即停止重发。
长度 2 始终只发 F1 头部；两个 console 片段分别为长度 10 和 13。
表中 OUT 数是主机尝试数，不是设备重复执行次数或可靠投递率。

| 抓取 | 路径 / OUT 次数 | 实际结果 |
|---|---|---|
| baseline-boot | Windows 被动抓取，无 RX 发送 | 13,687 帧；TOP_CFG=11、original=0，shell 启动 |
| baseline-ctrl-u | Windows / 1 | 新 tty byte=15 回执 |
| native-echo-a | Windows / 3 | 0 字节，未确认受理 |
| after-native-empty-ctrl-u | Windows / 2 | 新 tty byte=15 回执 |
| libusb-native-b | libusb / 3 | 长度 10 全 payload，R43B 与提示符完整 |
| libusb-dmesg-tail | libusb / 1 | 长度 11 全 payload，完整 tail；没有 echo A 的 RX 记录 |
| libusb-stty | libusb / 3 | 三个 OUT 完成，0 IN、无回执；不能声称 shell/termios 失败 |
| native-echo-c | Windows / 1 | 长度 10 全 payload，R43C 与提示符完整 |
| compatible-stty | 原逐字终端 | 9 字节受理、10 次重试，stty 设置与提示符读回 |
| native-console-prefix / suffix | Windows / 2、2 | 两帧全 payload，R43D 与提示符完整 |
| f1 | Windows / 2 | 新 reboot2 回执；另指定 62bc28a1 得到 fastboot msmnile |
| final-boot | Windows 被动抓取，无 RX 发送 | 13,677 帧；TOP_CFG=11、original=0，shell 启动 |
| final-native-echo | Windows / 2 | 重启后完整长度 10 payload、R43F 与提示符 |

这些抓取解帧均为 0 stray、无残留；此统计不代表 TX 无损。
新 Windows/libusb echo、原生 console 和重启后的 echo 显示正常 shell 执行和可见
响应，未在这些受理样本中复现真正的缺命令输出。没有把缺回执的轮次归成受理成功。

libusb 使用 bulk OUT 0x02 / IN 0x81，最大包 16、read-size 16，无 setup/reset。
echo B 的三次 12 字节 OUT 在 usbmon 均为 completion status 0；第三次之后才收到
一个完整设备回执。stty 的三个 10 字节 OUT 也完成，却没有收到回执。这说明已修复
等待配置下绕过 qcusbser 仍会缺回执，不能把问题全归于 Windows 串口驱动。
usbmon 是 WSL 虚拟控制器的 URB 记录；它不证明物理总线 ACK，也无法给无序号
的回执绑定具体哪次重发。

## 43.4 源码审查与工具修正

详见 [source-audit.md](../reference/rx43/source-audit.md)，含准确版本、SHA256 和来源。

* RX 整帧锁、TOP_CFG 回读、flip buffer→line discipline、串口 TX 队列、console
  writer 与 shutdown drain 已核对；插入计数、用户读取、命令执行仍是不同阶段。
* 实际 init 用 ttyEUD0 启动 sh -i；BusyBox 是 1.37.0。核对官方同版本源码并用
  实际二进制做 QEMU PTY 复查：单次 15 字节写入得到 echo 输出/提示符，未回复
  ESC[6n。没有普通 ASCII burst 因光标查询而被吞掉的证据。
* PTY 中行编辑暂时关闭 ICANON/ECHO/ISIG；手机 stty 命令执行时读到恢复后的
  canonical/echo 设置，符合该模式切换。终端过滤 ESC[6n 的兼容行为保持原样。
* 解码脚本现在显示完整 stdout。eud-step 直接保存完整 `.txt` 和发送/回执/统计
  `.events.txt`，拒绝覆盖原始捕获，检查完整帧及 F1 保留长度；增加有界 TailSeconds。
  仍是一次一个帧的手动工具，没有自动串命令、刷机循环或序号去重。

## 43.5 验证、保留状态与下一步

reference/rx41 全部原始哈希及增强 verifier 通过；reference/rx43 新原始/usbmon
哈希、完整输出/console/F1/USB completion verifier 通过。PowerShell AST 无语法错误，
增强的单步工具已在 echo C、原生 console、F1、重启后 echo 上实际运行。
发布前同步 Windows/WSL 镜像并要求 docs-health-check RESULT: clean，只推 fork/master。

最后实时状态：Linux shell、原 RX41 ordered 候选，TOP_CFG=00000011、original=00000000；
重启后原生 echo R43F 第二次 OUT 得到完整 payload、响应和提示符。
9501/9500/9505 均 OK，COM14；所有串口 owner Closed/Disposed，usbipd 6-5 Shared、未 Attached。
保留镜像与回退镜像仍是 session 41 §41.5 的文件和哈希。

下一轮聚焦缺回执，先查这次持久 dmesg 和两个 USB 路径的原始证据。
如果加内核诊断，应保持原整帧 DAT/锁/等待配置，先记录现有 STATUS1 轮询的空闲、
pending、无效头部与接受帧计数，放在可事后读取的持久统计里；进一步读空闲 ID/LEN
前核对读副作用。用这些新数据区分门控/拒绝路径，再决定是否改变中断或轮询策略。
不要无新依据原样重跑旧 0 等待 DAT、极速轮询、timeout/reset、长 dd 命令。
尚未取得缺回执的硬件根因或长期稳定性证明；当前协议仍有 ACK 丢失后重复输入的可能。
