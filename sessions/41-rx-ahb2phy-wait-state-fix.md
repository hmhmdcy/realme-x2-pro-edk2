# 41. SM8150 AHB2PHY 等待周期使原生多字节 RX 推进（2026-10-09）

**已找到并重复验证原生 RX 的有效方法：SM8150 SOUTH AHB2PHY TOP_CFG
（0x088ee010）设置为 0x11，确认回读，再在 TX 锁内读完整帧。**
UEFI 跨两次重启均得到 ABC=`41 42 43`、DEFG=`44 45 46 47`；Linux
也取得两次 ABC、三次 DEFG 的完整受理结果。长度 14 的完整 payload
随后在 Linux 中读对。不是单字节主机拼接，也不是通过修整期望值判定成功。

下一会话交接与短提示词见 [session 42](42-native-terminal-next-session-handoff.md)。
**2026-10-09 session 43 更正：** 核对未改动的 `.raw` 与 SHA256 后，确认本节
曾误报缺输出的原生 id、14 字节 echo 和 console 实际已有完整响应。
解码脚本当时只在 stdout 打印 `eud:` 行。更正证据及本轮实测见
[session 43](43-native-terminal-evidence-audit.md)；缺回执仍存在，不能扩大为长期稳定。

## 41.1 从真实 SM8150 地址表补上写入依据

session 40 的 SDM845 表不能直接授权本机写入。这次继续审查原厂 RMX1931
`BOOT.XF.3.0-00501-SM8150LZB-1` 的 DALSYSDxe，并用公开 DalHWIO.h
结构布局解析 PE 指针：region stride 40、module stride 24，RVA 经 PE section
转文件偏移，模块 offset+length 不超过 region 大小。

结果是 **AHB2PHY_SOUTH=0x088e0000，SWMAN offset=0xe000**；
本机 NORTH 在 0x00ff0000。当前工作 DALSys.efi 与新下载原厂文件 blob 不同，
但两者的物理映射相同。没有替换或运行下载的二进制。

同机型 Realme 原厂 dwc3-msm.c 定义 TOP_CFG offset 0x10、
ONE_READ_WRITE_WAIT=0x11，并有读配置、条件写 0x11、mb 完成后再用 PHY 的路径。
完整固定来源、blob/SHA256 和最小解析索引见 [reference/rx41](../reference/rx41/README.md)。
这次依据是实际 SM8150 映射与同机型源码的结合，不再是跨 SoC 地址猜测。

## 41.2 先只读，再做可恢复对照

先核对 9501/9500/9505、COM14 与 Linux 回执。BusyBox 没有 devmem applet；
两次长 dd 命令未完整输入，工具在无 ACK 后停止且未提交换行，再用 Ctrl-U
取得新回执清行。直接用 `od -j /dev/mem` 也没有取得目标值：该 applet 对
字符设备用 read 丢弃数据来跳过，不是 seek。不能把错误当寄存器不可读或为零。
实际 BusyBox 的 dd 经 qemu strace 确认使用 lseek，但没有据此声称已读本机 MMIO。
这些失败路径不应原样重跑。

改用 EudSnapshot：先预载原 Kernel，升高 TPL 排除已知固件 TX 定时器，
读取 0x088ee010 两次、间隔 1 ms，之后才输出。两次均为零。
输出重复五次的是缓存值，不是十次 MMIO 读取。随后接续原 Linux。
snapshot-passive 为 13,944 帧、0 stray、0 主机 RX 模式发送。

EudWaitProbe 保留 RX39 的紧轮询和相邻 DAT 读取，只增加以下配置对照：

1. 原值必须为零，否则跳过、没有写入。
2. 写 0x11，完成屏障，两次回读均须为 0x11，才进入 ABC/DEFG。
3. 每帧先读 STATUS/ID/LEN，再连续读 LEN 个 DAT，期间没有 TX、printk 或延时。
4. 缓存结果后输出，恢复原值零并回读，再启动原 Kernel。

两次重启分别得到：

| Capture | ABC 原始 32 位读数 | DEFG 原始 32 位读数 |
|---|---|---|
| wait-native | 41414141 43424242 00434343 | 45444444 45454545 47464646 00474747 |
| wait-native-repeat | 42414141 43424242 00434343 | 45444444 46454545 46464646 00474747 |

COM 字段只取低 8 位。FIFO 推进后高字节不再总是相同，不能把一个 32 位读数
拆成四个 payload 字节。两次都明确回读恢复零。
主机每种模式均用了两次 OUT；第一份抓取 8 stray、第二份 0 stray。
完整受理结果有效，但不能把它扩大为无损 USB/TX 证明。

## 41.3 Linux 本地接入和重复验证

基于现有已修改的 eud.c 小步接入，不重置用户内核工作树。驱动只匹配
qcom,sm8150-eud-com；映射已确认的 TOP_CFG，保存原值，写 0x11 并回读确认。
失败会恢复原值并报错。RX 改为 STATUS 门控后，在共享 TX 锁内缓存整帧，
每次 DAT 只取低字节；读完后才打印或交给 tty。F1/卸载路径恢复原配置。

先保留多字节为诊断，取得以下完整、独立的受理结果：

* linux-abc-1、linux-abc-2：41 42 43。
* linux-defg-1、linux-defg-2-jitter、linux-defg-3：44 45 46 47。
* 每次读完 STATUS1=06060606，即低字节 RX pending 清除。

linux-defg-2、linux-defg-2-retry、linux-abc-3 都是 0 字节抓取，没有受理证据，
不计成功，也不计设备读错。加入可选 RetryJitterMs 后既有受理也有空抓取，
不能声称它解决了整帧受理问题。单字节 Ctrl-U 另有新回执，设备并非据此可判宕机。

## 41.4 原生 tty 与输出区分

验证原生读数后才允许 len 1、3..14 进入 tty；len 2 继续保留 F1。
中间候选读对了 `id\n`、`id\r` 和 14 字节 `echo RX41-TTY\n`。
当时误写为只有驱动回执；session 43 核对原始抓取后确认分别已有
`uid=0 gid=0`、`RX41-TTY` 和提示符。批量 tty 插入计数也确认 `id\n` 投递 3 字节。

再发送单帧 5 字节 `X=ok\n`：受理回执和 tty=5 均取得。
随后原单字节终端执行 `echo $X` 返回 `ok`，证明原生多字节输入确实在同一个
shell 执行。赋值的第一次发送没有回执，
仅第二个有 ACK 的抓取算证据。

为减少帧回执与 tty 响应竞争，后续候选先打印完整帧回执，再投递 tty；
所有 RX DAT 已在打印前读完。用 tty_insert_flip_string 批量插入并记录不足投递。
最终 ordered 候选的原生 `id\n` 与两帧原生 console 命令的 14/13 字节均受理。
session 43 核对确认它们的原始抓取也已有 uid 和 RX41-C 输出及提示符；
旧的“未捕获”结论撤回。此前候选同样有完整响应，不能据此把 ordered 改动
称为输出修复。完整读数或 tty 接收计数仍不能代替所有命令响应验证。

当前候选的普通终端执行 `echo E` 返回 E；逐字符执行 `echo C>/dev/console`
的第二次完整尝试返回 C（21 字节含清行与换行受理、191 帧、0 stray）。
第一次尝试在 pathname 中途无 ACK，未提交换行，已经清行，不计 console 失败。
最终 F1 第一次 OUT 就有新回执；有界 `fastboot devices` 当次返回空，随后明确指定
序列号 62bc28a1 的 fastboot reboot 返回 OKAY，独立证实 fastboot 命令通路。
没有把空枚举记成看到了设备列表。最终重新启动同一候选，末次状态见下节。

## 41.5 构建与安全边界

本轮只刷 logdump；没有刷 boot 或其他分区，没有修改 PHY/时钟/中断配置，
没有 force bind、安装过滤器或变更 hrdevmon。每次 F1 取得新设备回执后，
另行有界核实 fastboot 序列号 62bc28a1，再执行下一步。
一次 F1 发送器过早开串口，因现有抓取占用而 Open 失败，未发送字节且 finally
关闭；之后等待抓取 Closed/disposed，再重新单步操作。原始空文件保留在外部输出目录。

每个 UEFI 诊断镜像的 Kernel、DTB 都与 rx33 基线逐字节比较。
Linux 候选由原 FAT 加入新 Image，DTB 逐字节不变；不调用会重建旧 initramfs
的 build-image.sh。实际 initramfs/init 保持 SHA256
`e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab`。
原 eud.c 保存为外部 eud-before.c，SHA256
`311e5508fccb8d6f0623ba21e7f5891e4fda45984ba9dd6c3a76168037c6d411`。
已有 DTS、rpmh.c、eud_earlycon.c 修改与备份均保留。

旧可回退镜像仍是 logdump-rx33-console.img，SHA256
`d5a36aa2152dd77735f1ea8861f05ad35cb7f714605d5c3cd9db106b6c5f8953`。
保留的 RX 核心候选 logdump-rx41-native-ordered-tty.img 的 SHA256 为
`cdf0c1eb633c906f424dfd33c4d7757e1cc1bfe6edd88002127da4ebbdca477f`；
Image `def8528ac0522c30cee6f5008ea6bb4b171514f6cf5d5c6cefbf185686c752c4`；
eud.c `425a22c6b08da820f946aa269d9d5cd141ae181d5d73dde71ec3cdb2d8e7628b`。

它是已验证 RX 推进、保留原终端/console/F1 的候选，**不是原生命令可见响应已全修复的声明**。
完整记录保留中间候选和空回执。reference/rx41/verify.py 从原始二进制抓取验证低字节，
SHA256SUMS 保证发布的 `.raw` 没有被文本换行转换。

最终同一候选重启：final-ordered-boot 13,898 帧、0 stray、没有主机 RX 模式发送；
TOP_CFG=00000011、original=00000000，Linux shell 启动记录完整。
末次 Ctrl-U 第一轮三次 OUT 没有回执；重新有界核对时第 2 次 OUT 取得新回执，
finally 已 Close/Dispose。9501/9500/9505 均枚举 OK，COM14；6-5 Shared、未 Attached。
没有用初次空回执冒充健康检查成功，保留 final-ctrl-u 与 final-ctrl-u-retry 两份原始记录。

## 41.6 尚未扩大验证的范围

当前结果已排除本机 COM 只能收一个 payload 字节的硬性限制。它不提供其他 SoC
的通用寄存器规格，也不证明所有 OUT 都受理、所有 TX 都无损。
整帧偶发无回执仍需明确 ACK/有界重试；本轮没有物理 USB 总线采样。
后续可单独改进 IRQ/整帧受理与 TX 输出稳定性，并把共享 AHB2PHY 配置迁入合适的
平台/DT 资源管理；不要因此重新原样做 0 等待状态下已失败的 DAT/轮询变体。
