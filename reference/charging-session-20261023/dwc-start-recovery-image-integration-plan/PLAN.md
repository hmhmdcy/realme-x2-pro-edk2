# #502 → 一致 DWC 同步恢复候选：只读集成范围

本叶只读检查实际冻结的 `/home/cy122/charging-management-20261023/gauge-image502-notify-01/{source354,build}`。没有 storage helper、挂载、编译、链接、旧测试、SDK/Git 或设备操作。根尚未批准本轮新 Image；本文不是执行入口。

`dependency-result.json` 绑定实际 #502 Image `085d0306…b25955`、CONFIG `23e088a9…0ed`、原 DWC 源、全部命中的 saved commands、对象和 archive。`inspect.py` 只扫描现有 9242 份 `*.cmd` 的精确 core.h 依赖字符串，并读取 archive/config/已冻结模块导入缓存；没有重新扫描 778 个模块 ELF。

## 必须重编的实际目标

| 目标（统一在 drivers/usb/dwc3/） | 当前链接方式 |
|---|---|
| core.o | built-in；分配/操作 struct dwc3 |
| trace.o | built-in；实际 core.h 依赖 |
| gadget.o | built-in；本轮 C 改动及新增 generation 字段 |
| ep0.o | built-in；实际 core.h 依赖 |
| debugfs.o | built-in；实际 core.h 依赖 |
| dwc3-qcom.o | built-in glue；实际 core.h 依赖 |
| dwc3-qcom-legacy.o | built-in glue；本板实际父驱动，实际 core.h 依赖 |
| dwc3-generic-plat.o | built-in glue；实际 core.h 依赖 |

该目录实际 `built-in.a` 为这 8 件加 `dwc3-of-simple.o`，成员顺序见结果原件。of-simple 没有 core.h 依赖，应保持原字节；不因同处一目录而重编它。`drivers/usb/dwc3/modules.order` 为空，全局 modules.order 也没有 DWC3 目标；HOST/DUAL_ROLE 未启用。此配置不需要重建 DWC `.ko`，不能只重编 gadget 而沿用另外 7 件旧布局对象。

新 `u64 err_event_seq` 插在 `err_recovery_count` 与后续 u2sel/flags 之间，是私有 struct 的布局变化。现有 `CONFIG_DEBUG_INFO_REDUCED=y`，原/新已编 gadget.o 的 DWARF 都只保留该 struct declaration；没有完整成员 offset。此处不猜偏移/sizeof，也不由“导出 CRC 没变”冒认 type ABI。8 件全部重新编译，才能让分配大小、成员偏移与实际 C/header一致。

## 最小来源与私有执行方式（待根放行）

新增 source 集合严格只有：

- `drivers/usb/dwc3/gadget.c`：冻结候选 `ca4bf1c5a1afa42267d2f7f8b636dfe7ca5a1b9581307093f93a892e2f004314`。
- `drivers/usb/dwc3/core.h`：冻结候选 `9a8dc48a1283db17b6a0cad01f0bc43ff916cfa7dc3a11b680c2145984f97a67`。

完整差异来自已独审的 `dwc-device-start-recovery-candidate/against-502.patch`。原 core.c、glue C、BQ 001407、config、release、DTB、bootargs和 initramfs 均不改变。本轮没有额外 PM unwind 补丁。

复用 `charging-ui-audit-20261023/gauge-image502-notify-candidate/run-502.py` 的已验复制/namespace/身份/链接与父终核结构；实际缓存不存在单独 `link-helper.py`。应从 #502 的三树 build/source354/input-initramfs363 复制到一个新的唯一私有目录、无 hardlink 写共享，加私有 tmp。child 先验证独立 mount namespace 与 recursive-private，再只在 child bind 到原四 canonical 路径。父源/配置/缓存/挂载、冻结502三树均前后核对；不用旧有状态输出目录。

只在私有 source 替换上述两件，保留其余源和现有工具链/Rust1.99环境；原 reproducible timestamp `Tue Oct 20 03:03:47 UTC 2026`，实际 UTC 另记。新 KBUILD_BUILD_VERSION 由根指定，不能仍冒用 #502；UTS_RELEASE/config 不变。

沿原 make argv（`ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- LOCALVERSION=+ W=1 V=1 -j4`）先显式编译上表 8 个 object target，然后仅运行 `Image` 目标完成正常 archive/link/kallsyms/Image 流程。不用 modules、dtbs、全量 firmware 或新配置；不手改 thin archive、不塞当前独立0718对象代替canonical路径一致编译。每个真实 child 持原 PID/argv/日志并等同一终态，未知不重放。

## 构建硬门与 ABI 范围

实际原 vmlinux archive 3247 叶，libstub 32 叶。允许 archive 叶变化集合是上表 8 件及新身份的 `init/version.o`；8件中某些编译后字节相同可以接受，但真实目标命令必须全部完成。其余 **3238** 叶与32stub逐字原#502。archive 外 `init/version-timestamp.o`、kallsyms 临时对象、vmlinux.o/System.map/Image 等仅按原链接生成，不能借它扩大来源集合。版本对象须沿原 metadata proof 精确证明仅身份字符串变化、可执行 section 不变。

原 cpio、gzip inc 与 usr/initramfs_data.o 必须保留原 SHA；所有 CONFIG/release/public headers（不含本次明确改变的 DWC 私有 core.h）不变；源 delta 恰两件。任何额外叶、ramfs 或配置变化即拒绝并留原件，不临时扩大许可。

已有 #502 vmlinux 有15个 dwc3_* 导出。过滤已冻结778模块导入原件及当前481四新模块缓存，没有这些导出的导入者；这只是已缓存集合的静态范围，不代替新的 runtime attestation。当前 in-tree depfiles也没有 DWC模块目标。因此最小构建不需要新 `.ko`；未来一致Image仍应核实际ELF导出集合及symvers的15097全行/命名空间/类、原模块接口/设备调用者范围，并保留原CCI补充来源。CONFIG_MODVERSIONS关闭，CRC全0不是独立 type ABI证明；未知未来外部模块/任意gadget function不在本结论内。

本轮只填 start errno→局部清理→已有同步恢复漏口。core PM仍忽略gadget primary、保留 initialized/powered-success 与pending尾；HALT/soft-reset失败及负返PM的安全unwind缺口未改。任何新Image也只能称局部候选，不能据此声称实体待机、NCM重枚举或整机恢复成功。无载体/刷写/部署计划在本叶执行。
