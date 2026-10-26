# Session88：Wi-Fi依赖内核、只读固件服务及部署前交接

2026-10-10，Asia/Shanghai。按用户要求继续 Wi-Fi，充电阶段保持收尾；本次更新记录当前进展，供下一会话继续。

Wi-Fi 尚未可用。手机仍运行 #86，宿主 #89 依赖内核与只读固件服务已构建完成，但未部署，也未启动 MPSS。下一步应先更新 **EDK2 内嵌设备树**并构建实际 boot 固件，再验证 MPSS/WLFW 与实际芯片、板卡身份。

## 当前实机状态

USB SSH 本次采集：boot ID `32bf2d8f-8dde-47dc-9b88-e87db9e95198`，内核 `7.3.0-rc6-rmx1931-samurai+ #86`，uptime 3984.69 秒，taint 0。网络接口只有 `lo`、`usb0`；remoteproc 类没有实例，I2C 客户端只有触摸 `1-0020` 和电量计 `2-0055`，没有 MP2650 客户端。

显示超时累计 2、下溢 0，display trace 已停止、snapshot 触发计数 0。现场 snapshot SHA256 仍为 `550d76908bd09bb280f57a5937fce7ec0101e4c167fed850b42834085e53f2f2`，与86/87一致。此次保存完整 dmesg、snapshot、主 trace、DRM state、kms，设备端摘要逐一核对。本轮没有清空/重武装 trace、开关屏、重启或分区写入。

## #89候选内核

沿用87已经经过真实 Kconfig 解析的最小诊断片段，27项语义配置变化。QRTR/GLINK/QMI/PAS/SYSMON/PD、RFKILL/mac80211/ath10k SNOC 等依赖内建，避免原 initramfs 没有 `/lib/modules` 的缺口。实际 `make olddefconfig` 与 Image/DTB 构建完成，构建退出码 0。

第一次构建守卫因 Kconfig 自动生成的版本注释变化而退出，尚未执行 Image 构建。核实仅注释头变化后更新私人候选基准，再构建成功；没有额外配置值变化。最终构建日志未检出 warning/error。

本轮源码只增加 MPSS DTS 的两项语义变化：`status = "okay"` 和本机 `firmware-name = "qcom/sm8150/realme/samurai/modem.mdt"`。同一源码的 PAS 描述 `auto_boot = false`、PAS ID 4，故候选仅暴露显式启动入口。Wi-Fi 节点仍 `disabled`，其余设备树节点、属性和 phandle 保持。

| 私人产物 | 字节数或意义 | SHA256 |
|---|---|---|
| Image-wifi | #89，39160320字节，未部署 | `02fbe7e5d20cc2a0f5b55e08511ee9a1a39d2c47516079569fe8dc2368360ea0` |
| samurai-wifi.dtb | MPSS两属性增量，96892字节 | `7a5e5ffb15baf3548b92671fb6f638a587911b40e936ce2ddf92ff13728096d9` |
| config-wifi | 27项配置语义变化 | `981b4b828e5e6a8a108a7bff1c8fa7ccb8133abcf6ffd0ec0c631fbbca4f44ff` |
| 原CPIO | 保持既有init/USB/SSH身份 | `74052b3e705e5af1c2268590206da264a339cf4e042e5ed601c54f56ad66b102` |

审计核对30项此前源文件的内容/模式，除本轮 DTS 增量全部保持；14个 initramfs 文件和308个链接保持。87的显示 timer 候选及86的 MP 观测修正随 #89 保留，尚未实机验收；MP没有持久 DT 绑定。

## 本机固件与服务域

只读挂载本机 modem 分区 `/dev/sde4`，核对 PARTNAME、524288扇区、UFS型号及固定 boot ID，归档33项文件：30个 `modem.bXX`、`modem.mdt`、两个服务描述。归档 SHA256 `8fcddffc38adb569180091751787748a6dd11959962ec2afd10c540c6c8e4c9f`，逐文件核对摘要。

分区读取前后 SHA256 相同：`88af46265a4f23c634b2a3c0a4be6815caf796f4b3bb398a6223a565c9e132f0`。挂载结束已卸载；未读取/提供 modemst 等 NV 存储服务。初次库存脚本的 UFS 型号守卫多写一个尾随空格，在挂载前退出；按实际一个尾随空格修正未封存脚本后通过。

MDT 为 ELF32、machine 164、33个程序头；实际 LOAD 段均可重定位，跨度 `0xa000000`（160MiB），与既有 MPSS 保留区 `0x8dc00000` 起160MiB一致，结束于 Venus 区起点。此检查证明布局符合，不证明签名接受、实际加载或运行成功。

本机服务描述为 `msm/modem/root_pd` 与 `msm/modem/wlan_pd`，QMI实例180；无线域提供 `kernel/elf_loader`、`wlan/fw` 等。当前本地主线源码 PD mapper 已有对应 SM8150 无线域，无需据此另写 PD mapper 补丁。35项 Wi-Fi 固件沿用81/87的私人归档校验；实际 chip/board ID 未知，不能任取某个 bdwlan 当默认。

## 只读固件服务与测试

通过 gh 获取固定主来源，完整第三方源码仅留私人目录：

- [qrtr固定提交](https://github.com/linux-msm/qrtr/tree/29e36ae164389580a0f8ea7a7fdb728140ae978d)，构建静态 AArch64 `qrtr-lookup`。
- [tqftpserv固定提交](https://github.com/linux-msm/tqftpserv/tree/128cd6e0a39734fefd0f0bf0aad5e997c29e2445)，增量修改后构建 `tqftpserv-ro`。

原服务支持 WRQ 和 `/readwrite/` 路径，不能直接用于当前固件实验。增量实现明确拒绝 WRQ、可写 open flags 与可写命名空间；指定 `SAMURAI_TFTP_FIRMWARE_ROOT`，只在该目录逐层 `openat(O_RDONLY|O_NOFOLLOW)` 打开文件，拒绝绝对后缀、`.`/`..` 与符号链接。没有创建文件/可写目录/向 writers 队列添加传输的入口。

测试从实际修改后的源码提取 WRQ 函数，链接实际路径翻译器和安全打开函数：三种只读路径读取正确，写 flags、可写命名空间、路径逃逸、中间/末端符号链接均拒绝；正常及最小 WRQ 返回只读访问错误，目标文件未创建。编译/运行退出码均0。测试使用本地文件系统与 socket 桩，**不代表实际 QRTR 协议、手机固件服务或 MPSS 已验证**。测试编译日志仍含原压缩桩两个 unused-parameter warning；工具构建日志无 warning。

两个私人可执行文件 SHA256：`qrtr-lookup = 11f5a225470b536b5dd0a9e181059447b696f4e89c2884ee28e5d6d48bb32074`；`tqftpserv-ro = 274fd4fd849fb9e49853eefd7923f86a7554af9ecf664a324ae72b498f19ec18`。工具尚未传至手机或运行。

## 实际设备树与下一步

本项目 PlatformBm 没有 `dtb=` LoadOptions，DtPlatformDxe 向 EFI 配置表安装固件内嵌设备树。当前入口为仓库 `Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb`；该文件 SHA256 本轮仍为 `872fd9f83382143977c2406c0a869bcac5c051f0f27350ddf3676f043572587b`，未改动。**只把新 DTB 放入 logdump FAT 不会启用 MPSS**，需新 boot 固件。来源和既有结构核验见68/79。

1. 使用#89 DTB构建实际 EDK2 boot 固件，先保存旧 DTB/FV/boot，审查仅 MPSS 两属性变化及固件版本变化，保留兼容 DTB、BootShim、模块、Android头和原引导参数。当前没有新固件构建，也没有 FAT 候选。
2. 保存新鲜实机现场，完整备份当前#86 boot/logdump；采用新守卫完成已授权 boot/logdump 部署，核对实际 `/proc/device-tree`、remoteproc offline、QRTR和现有 USB/EUD/触摸/电量计。
3. 临时 RAM 目录安装并校验本机固件与工具，指定只读根目录，审查显式启动条件后验证 MPSS/WLFW/PD/TFTP及实际 chip/board ID。不要启动未审阅 rmtfs/NV 服务。
4. 选择精确板数据，接入 Wi-Fi 节点，验证无线接口、扫描、连接与实际流量。之后继续蓝牙/音频等全硬件目标。

充电保持待办；本轮无充电配置、解封、NVM/OTP、FET/OTG、GPIO/MCU操作，无 OEM charger probe，未访问0051/0053/0072或故障REG14，不用 I2C_FORCE。显示故障快照保留，不自动开关屏。没有权限/审批阻挡。

## 证据与交接

[reference/kernel88](../reference/kernel88/README.md) 保存自有增量源码/patch/脚本、构建与测试记录、固件摘要、保留审计和实机日志。`SHA256SUMS`覆盖同目录全部文件（不包括自身），历史85/86/87封存核对保持。完整源码/固件/JSN/配置/生成头/镜像/二进制/身份留 `E:/edk2-samurai-out/kernel88`，不发布。

会话结束点为“#89和只读工具完成，实际固件部署前”，全硬件目标未完成。下一会话提示词见 [NEXT-SESSION-PROMPT.md](../NEXT-SESSION-PROMPT.md)，完整步骤见 [NEXT-SESSION.md](../NEXT-SESSION.md)。
