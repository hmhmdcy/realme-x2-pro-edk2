# 原 BdsDxe 私有基线重链接

本次基线通过。仅重链接缓存原41库并执行原 GenFw 转换，未调用 make、AutoGen、库源编译、GenSec/GenFfs、全固件构建或封装；没有编译 R2，没有设备/SDK/Git 操作。

执行器 `run-baseline.py` SHA `ad66353d080dd9bdffa9c26d7fa00823730ade884a9e89ebd564fd90cd006667`。实际缓存 GNUmakefile 的两条命令、展开后的完整 argv、原响应清单、工作目录和返回值均保存在 `result.json` 的 child 字段；只把工具名固定到已核 SHA 的实际工具路径，`ARCHCC_FLAGS` 按原未定义空值、`EDK_TOOLS_PATH` 指向现有 BaseTools，保持其余原链接参数。

唯一输出目录是 `E:/edk2-samurai-out/charging-management-20261023/eud-bds-baseline-private-01/`。先完整复制 Bds 模块 builddir 并逐文件核对，再启动 `/usr/bin/unshare --mount --propagation private --fork`。child 在 bind 之前核实自身 mount namespace `mnt:[4026532221]` 不同于 parent `mnt:[4026532210]`，并逐条确认 mountinfo 无 shared/master/propagate_from。随后仅在 child 将私有 Bds 目录 bind 到原 Bds 模块路径，核 inode/device 相同，才运行链接/GenFw。父环境没有执行 mount/umount；child 退出后其私有映射随命名空间消失。

新 ELF 与原 `DEBUG/BdsDxe.dll` 整文件相同，SHA `7bb467d07b4d3a013f36677f90d58b18a435ad48edb48e7b35e05aa809e27341`。新 EFI 与原缓存以及之前独立抽取、已核 SHA 的 a30 实际 PE32 整文件相同：114688 bytes，SHA `8d72c4a69a64ab1f8e5f0b139daf34dfb0dbfe22113eb66ceac8ca839e71697e`。没有忽略或归一化任何字节，原完整 ELF 路径字符串也保留。

父环境189个相关文件（原41库、Bds 模块缓存/Makefile/EFI、平台源码/INF/编译依赖、工具与封装输入）的 SHA/size/mtime 和目标 mount chain/namespace/inode/device/完整 mountinfo SHA 前后完全相同。`parent-before.json` 与 `parent-after.json` 自身 SHA 也相同，均为 `a93dcd67ff738705994e87c913e2579f1f6b8e56ab3f80dec7a46de2f694f3a3`。

原 stderr 已保存：链接有一次 serial LTRANS warning 和一次 RWX LOAD segment warning；GenFw stderr 为空。未改变选项来消除告警，新旧 ELF/EFI 字节一致。这里不声称零告警，也不将旧 RWX 段扩大为新的功能结论。

公开及私有 `result.json` 字节相同，SHA `534373bc829f384e817580e7f2a9dd8700f4366cf51560cece7206c7e8e27ad6`。私有目录同时保留 child mountinfo、父快照、两条命令 stdout/stderr、原复制输入及新 ELF/EFI，不重放该唯一目录。

这补足了“同工具链/原库可以私有重链接复现 a30 Bds 模块”的执行证据。R2 两行静态审阅仍复用原收据，没有重跑其测试；R2 平台库候选编译、其余固件模块保持、最终封装和实际 boot/CSR/USB 验证均尚未进行，须根会话另行决定下一步。
