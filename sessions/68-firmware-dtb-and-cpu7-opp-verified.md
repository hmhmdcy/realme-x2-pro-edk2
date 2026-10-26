# 68. 固件 DTB 激活，CPU7 高 OPP 真机通过（2026-10-10）

**CPU7 的 2956800 kHz OPP 已进入实际设备树，调频表与最大频率恢复，原启动报错消失。**
本轮只更新 boot 中的固件 DTB，沿用 session67 的 #60 Image/config/logdump，没有改
内核 C 源码、initramfs、EUD 参数或 Windows 驱动。完整新日志和状态文件均通过设备
SHA256/gzip CRC；CPU7 高频负载、温升和长期稳定性尚未测试。

证据：[reference/kernel68](../reference/kernel68/README.md)，离线核对为该目录 verify.py。

## 68.1 当前模式与回退基线

用户询问 COM14 是否归 Windows 时，实时 usbipd 显示 6-5/9505 Attached，WSL 已枚举
bus1/address9；COM14 只是保留的 Windows 名称，当时 Windows 不能同时使用。
没有其他已知 EUD owner，既有手动 helper 取得新 Ctrl-U 回执。设备仍是 #60、boot_id
28e3bd68-2dd4-46f5-a24b-95f237ec070b、taint=0。压缩 facts 240/267 字节校验通过。

通过 PARTNAME=boot 独立确认 /dev/sde11，只读其前 6678528 字节，存于手机 tmpfs。
完整读取 3261 个 2048 字节块，哈希为
`8c9dea12a8eca687f9da59e067da8c3dfb91bec4d61ae3371c67292d434c7edd`，与原
boot-samurai-f1.img 和构建前副本一致。元数据压缩169/解压213字节校验通过。
这证明启动镜像有效前缀相同，没有把整个96MiB分区的尾部填充声称为已比较。

## 68.2 修正实际 DTB 部署路径

session67 的候选 DTS/DTB 已编译，但仅放 FAT 时 live DT 明确 OPP_ABSENT。
PlatformBm.c 的 LoadOptions 没有 dtb=；DtPlatformDxe 把固件 DTB 安装到 EFI 配置表。
本轮更新实际被跟踪的
Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb，再使用既有 build.sh
的 samurai/GCC5/--skip-rootfs-gen 增量构建，没有调用旧 build-image.sh。

新旧 DTB 全树属性比较严格只有新增 /opp-table-cpu7/opp-2956800000：opp-hz 为
2956800000，opp-peak-kBps 为8368000/51609600。来源及硬件 LUT 依据仍是
[session67](67-usb-provider-and-dtb-activation.md) 的固定 SoC 树与本机日志，不改固定电压。
所有 EUD/PON/bootargs 属性保持原值。

离线验证解开 Android boot gzip、LZMA 和各固件文件：BootShim144字节、兼容 DTB、
cmdline、模块集合均保持一致，FDT RAW section 与候选字节相同，FV/FFS 校验通过。
101个主固件模块中，除 DTB 外的差异只是三个模块中的 UTF16 版本号2184dc1→2d389cf；
compact 的 Sec 同样只变版本字符串。严格替换比较证明其余可执行字节未变。
实际配置的 FD 为7MiB、Android page为2048、ramdisk为1字节；旧核对脚本的20MiB假设
不适用于这里。独立 verifier 初始假设错误及修正均记录，未按错误假设部署。

构建退出0，仍有36条、8种原有表达式/RWX/LTO warning，未称无 warning；二进制
范围核对证明没有混入其他固件行为改动。原 Image/config/init 和两个 EUD C 源码哈希
全部不变。候选 boot 6682624字节，SHA256为
`785071a405d839b13d3d0ef040f42d227b09659e6dd0d3df96bb3689ced0635b`。

## 68.3 仅一次 boot 写入与完整日志

先关闭旧 owner，再用既有 F1 helper 单次发送9002，3030.899ms取得新 F1 回执，
随后3105.577ms EIO为重启断开，资源finally释放。独立 fastboot 核实62bc28a1、
product=msmnile、boot大小0x6000000，核对候选长度/哈希后只 flash boot，再 reboot。
写入与重启均 OKAY；logdump、userdata、GPT及其他分区没有写入。外层 finally detach
遇已经消失 busid 的报错保留，没有用它或 EIO 单独证明 fastboot。

冷启动只执行一次正常 com-up，三节点OK。WSL attach 后首 lsusb尚无9505，等独立
枚举出现bus1/address10后才使用原 helper，没有reset/setup/ZLP/自动解绑。
启动首先把 dmesg 保存为 /tmp/K68L 并压缩；原件在采集结束后仍留在手机。

| 文件 | gzip字节 | 原始字节 | 校验结果 |
|---|---:|---:|---|
| 新完整dmesg | 12377 | 52842 | 设备SHA256及gzip CRC通过 |
| 新运行facts | 275 | 736 | 设备SHA256及gzip CRC通过 |

dmesg gzip SHA256为`20864da83deb7c9e8c795fa3eb68b06acd1a495bc483057ac9d67a076fe1923d`；
解压SHA256为`072040c4cabc3299c62e900775089627e92ba43c4f414db34b3d2f4544896e6f`。
facts gzip SHA256为`e52340e07e560cc3fdb1932964bcecc063a92178389771a71a35f925047c041b`。

失败抓取独立保留：旧启动第一导出在240秒关闭前无END，第二缺起始标记/哈希/数据；
新启动第一日志12371字节，少6字节，哈希/CRC失败；两个长状态命令在缺数据回执后
停止未发部分、未提交换行，新 owner Ctrl-U 清行。它们不能判为内核故障。
之后释放/detach，使用已安装兼容终端独立取同一保存文件，通过完整校验，未补字。
一次 Windows startup Ctrl-U 无回执且没有发数据；后两次既有原生终端各有一次仅
startup同步重试，数据帧只发一次。没有新增 EUD 实验、工具或参数调试。

## 68.4 实际结果与优先级

新 boot_id=afbbf870-b998-43d8-ab3d-42b3c68c0122、taint=0。live DT含
opp-2956800000；policy7 的 scaling_available_frequencies 包含2956800，
cpuinfo_max_freq/scaling_max_freq均为2956800。瞬时频率1401600，未强制最高频或压测。
完整日志中原两次 Voltage update failed、invalid初始频率/无效哨兵均消失。
UDC a600000.usb仍存在，UFS6个LUN正常，无panic/Oops或旧early ioremap WARN。

| 优先级 | 剩余证据 | 后续范围 |
|---|---|---|
| P1 | UDC存在，实际USB通信未验证 | 读role/gadget/提供者配置，确认合法通信路径；不预设reset、拓扑或驱动参数 |
| P2 | PM8009 ldo2找不到ldof2资源地址 | 对照本机原厂PMIC/固件cmd-db，不删除节点来静音 |
| P2 | RPMh读回120次ret=-95，aux_bridge取drm_bridge为-ENODEV | 保留既有不支持读回兼容；区分原生显示/DP图和可用simpledrm |
| P3 | PSCI PC mode -3、无KASLR seed、init tail EINVAL | 记录实际影响，不能当宕机证据 |

燃料计、充电、原生面板/触摸/GPU/Wi-Fi仍待本机证据与硬件验收。CPU7当前结果只证明
节点生效、调频表恢复和该启动报错消失，未证明高频长期稳定。持久 rootfs 仍须保留
Android及全部数据，没有建立可安全覆写的大分区，见 ROOTFS-PRESERVE-ANDROID.md。

## 68.5 关闭与提交

所有WSL抓取正长度IN等于其raw，完整失败抓取未修整；Windows原始raw独立解帧验证。
Windows与WSL helper均使用finally，sink排空、workers结束；没有同时开两个owner。
末次三节点OK，COM14在Windows，6-5 Shared/未Attached，无已知owner/临时日志/ETW。
原驱动oem102.inf2.1.3.5、安装终端、eudtool、RX53/RX48回退文件哈希保持一致。
TOP_CFG0x11/整帧/RX53 console IRQ/F1/两种终端保持，F1仅在本轮刷boot前触发一次。
新固件F1源码及PON属性保持字节一致，没有为了验证它增加一次重启。修改只推fork/master。
