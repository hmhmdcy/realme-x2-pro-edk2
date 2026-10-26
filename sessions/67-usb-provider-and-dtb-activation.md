# 67. USB PHY 内建生效，CPU7 DTB 候选未进入实际启动树

**USB 控制器初始化已有真机改善；CPU7 OPP 仍未修复。** #60 回读确认主 HS PHY
与 dwc3 已绑定，`/sys/class/udc/a600000.usb` 出现，devices_deferred 为空，taint=0。
这只证明提供者及控制器初始化，不证明 USB 网络、gadget 功能或外设通信已经可用。
当前 COM14 已释放给 Windows，USBIP Shared/未 Attached，三个 EUD 节点 OK。

完整日志、失败导出和离线核对见 [reference/kernel67](../reference/kernel67/README.md)。
前次三项真机修复与 rootfs 研究仍以 [session66](66-verified-kernel-logs-and-builtins.md)
为准。用户要求保留 Android 和全部数据，仍未确认安全的大 rootfs 分区。

## 67.1 已校验的启动事实

操作先核对 Windows 设备、USBIP、已知 Windows/WSL owner；COM14 名字存在不代表
Windows 正在持有。Attached 时 WSL 独占 9505，关闭 helper 后还须 finally detach。
最后回到 Shared 状态，Windows Ports 节点正常，没有打开另一个 Windows 串口。

| 启动 | boot_id | 完整 dmesg | 结论 |
|---|---|---|---|
| DTB-only #59 | `83952af2-74ee-4dad-9e01-16ee951d4c20` | 52982 字节，SHA256/gzip CRC 通过 | taint0，CPU policies 0/4/7 存在；CPU7 OPP 与 dwc3 core failure 仍在 |
| USB provider #60 | `28e3bd68-2dd4-46f5-a24b-95f237ec070b` | 53788 字节，SHA256/gzip CRC 通过 | taint0，HS PHY/dwc3/UDC 存在，当前 deferred 为空；CPU7 警告仍在 |

两个快照分别在设备 `/tmp/K67O`、`/tmp/K67U` 保存后压缩，导出核对 gzip 和原始
长度、SHA256。#59 更换 DTB 时 Image 未变，所以 uname 仍为 #59；新 boot_id 才能
区分此次启动。#60 Image 变更由新 uname、boot_id 和运行配置共同确认。
这两份完整快照都未发现 panic/Oops，不能扩大为长期稳定性保证。

首个 OPP 导出损坏 base64，首个 USB 导出缺 9 压缩字节，均保留为失败结果；随后
独立导出同一个设备文件通过，没有补 raw。USB 首 owner 的 facts 命令在一个回执
缺失后停止，没有提交剩余内容/换行；工具 finally 释放资源。后 owner 用一次有新
回执的 Ctrl-U 清理未完成行，再读取文件。不能把这次缺字/缺回执判为新内核故障。
所有 owner 只使用既有工具读取日志；没有 overlap、setup/reset、ZLP、掩码/延时
实验或 Windows 驱动变更。结束标记与设备 shell 提示符均先于下一条输入。

## 67.2 CPU7 候选：源码与部署判据分开

校验完整 #59 日志确认 CPU7 两次 `Voltage update failed freq=2956800`，随后
`4294967295 kHz` 被降到 2841600。实际 qcom-cpufreq-hw 对固件 LUT 中的频率和电压
更新已有 OPP；缺项使频率表项无效。原 SM8150 CPU7 表只到 2841600000 Hz。

从 [维护过的 SM8150 tree 固定提交](https://gitlab.com/sm8150-mainline/linux/-/raw/defb39db31e6e2de8d7319c77ad697f9581070bd/arch/arm64/boot/dts/qcom/sm8150-xiaomi-nabu.dts)
取得 Nabu 的 `opp-2956800000`，保留其 `<8368000 51609600>` 带宽，与本地较高档
SM8150 OPP 相同；电压继续从硬件 LUT 取得，没有写死电压。该来源是归档的维护树，
不是当前主线或同机型实测。原 Android `SM8150_Plus` 只佐证平台，不证明原厂频率表。

实际 DTS 只增加这个节点，定向 DTB 编译没有警告，FAT 抽取与新 DTB 完全一致。
但只刷 logdump 后，CRC 有效的 live-DT 回读是 `OPP_ABSENT`，CPU7 频率表仍到
2841600、boost 表空。复核 `PlatformBm.c`：它加载 FAT 的 `Image`，当前 LoadOptions
没有 `dtb=`，EFI stub 采用 DtPlatformDxe 安装的固件设备树。此前漏查了这个已记载
的加载路径；本次不能算 OPP 修复失败或成功，因为新节点没有进入 Linux。

候选源保留在 `linux-port/dts/sm8150-samurai.dts`，增量补丁 `0006`。Windows DTS
副本此前落后于实际树，同步的 EUD 节点/PON/bootargs 是既有工作内容，不能算新增
硬件改动。下次先落实可审查的固件 DTB 部署方案，再用 live-DT 节点和完整日志验收；
不要重复只换 FAT DTB 的刷机，也不要据此调电压或强制高频。

## 67.3 USB 最小改动与实际结果

核对实际 SM8150 描述、匹配表、Kconfig 和 Makefile：主 HS PHY 在 0x088e2000，
compatible 为 `qcom,sm8150-usb-hs-phy`，匹配 SNPS Femto V2。正确选项是
`CONFIG_PHY_QCOM_USB_SNPS_FEMTO_V2`，原运行值 `m`，当前 RAM initramfs 无模块。
QUSB2 reset 名称不能当驱动类型，已内建 QUSB2 不能替代该提供者。
主线 [驱动匹配表](https://raw.githubusercontent.com/torvalds/linux/master/drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c)
和 [binding](https://raw.githubusercontent.com/torvalds/linux/master/Documentation/devicetree/bindings/phy/qcom,usb-snps-femto-v2.yaml)
支持此识别。本次没有替换驱动源码或猜测 PHY 寄存器参数。

只将这个选项 `m -> y`，olddefconfig 差异严格只有一行，Image 编译无 warning/error，
modules.builtin 含对应驱动。复制当前 FAT 镜像只替换 Image，DTB 原样保留，抽取
逐字节比较通过。新 logdump SHA256 为
`cfbe4509da3e4455351c11cad6400af7cc4044f21cc3ba04e3927bd01c35e6d7`。

新 #60 facts 压缩 341 字节、解压 650 字节，哈希/CRC 通过：

* `88e2000.phy/driver -> qcom-snps-hs-femto-v2-phy`。
* `a600000.usb/driver -> dwc3`，UDC 节点存在。
* devices_deferred 为空，运行配置为 `y`，taint=0。

完整 dmesg 的旧 `dwc3: failed to initialize core` 消失。约 26 秒的 supplier deferred
是启动中间状态，不能当成仍未完成：稍后的绑定和空列表确认其已解决。UFS 六个
LUN 仍挂接，原早期映射 WARN 没有重现。未配置 USB 网络/gadget、未测试外设，
尚无 native USB/EUD 共同工作的传输结论。

## 67.4 实际异常与下一步优先级

| 优先级 | 已确认事实 | 处理范围 |
|---|---|---|
| P1 | CPU7 两次 2956800 OPP 报错，初始频率无效；新节点未进入 live DT | 先修正 DTB 部署路径并验收实际树；候选未验证，不再猜电压 |
| P1 | USB 提供者/控制器/UDC 已恢复，尚无 gadget 或外设测试 | 以已绑定控制器为起点，分别确认 USB role、gadget 配置与实际通信；不先改图、reset 或 SuperSpeed 参数 |
| P2 | PM8009/cmd-db 与固件 RPMh 不支持的读回仍待核对 | 区分 PM8009 资源缺项与已有 -95 兼容行为，按同机型证据处理，不能删除继承节点来静音 |
| P2 | aux_bridge 取得 drm_bridge 报 -ENODEV；simpledrm/fb0 工作 | 原生显示、DP graph/GPU 和触摸尚待移植，保留当前可用显示与日志 |
| P3 | 初始 console 警告、PSCI PC mode -3、无 KASLR seed、init tail EINVAL | 记录真实影响，不把用户空间日志写入限制或后续已成功项当成 panic |

燃料计、充电、原生面板/触摸/GPU、Wi-Fi 等仍未通过硬件验收；不把其他机型参考
直接当本机参数。保留 Android/全部数据；仍只允许 boot/logdump，没有建立可安全
覆写的大持久 rootfs 分区。详细研究仍见 ROOTFS-PRESERVE-ANDROID.md。

## 67.5 保留项与关闭

仅两次 logdump 写入，均先关闭旧 owner、取得单次 F1 新回执，再独立确认 serial
62bc28a1/product=msmnile。F1 后 USB EIO 是回执之后的重启断开，单靠 EIO 不作成功
判据；outer finally detach 遇已消失 busid 的报错保留。冷启动只执行一次正常 com-up。
USBIP attach 后先等独立 lsusb 看到 9505，root WSL shell 保持在线。

TOP_CFG=0x11、整帧 payload、RX53 console/IRQ、F1、原生/兼容终端、RX48 回退和
真实 initramfs 均保留。eud.c、earlycon 源码、原 Windows 驱动/终端/回退文件哈希
与前次相同；没有调 EUD reset、掩码、延时或安装驱动。最后 umount 临时 debugfs，
helper finally dispose、workers 结束、sink 排空，outer finally detach；COM14 Windows
Ports/三个节点 OK，Shared/未 Attached，无已知 owner。只提交源码/诊断证据和文档，
修改仅推 fork/master，整体硬件可用性目标仍未完成。
