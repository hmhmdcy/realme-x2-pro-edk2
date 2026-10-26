# 未部署的 R2 BDS 私有候选

本轮通过原缓存命令，仅编译冻结 R2 的 `PlatformBm.c`、归档对应平台库，再链接 BdsDxe 并执行 GenFw。未运行 make/AutoGen，未重编其它库，未生成或封装 firmware、FD、FV、FFS、boot.img，未访问设备、SDK、Git。冻结 R2 单元测试没有重跑；先前逐字复现 a30 的基线收据 `534373bc…27ad6` 原样引用。

执行器 `run-r2.py` SHA `135f68fb3f3c073f06c011d8fdcd35387b07120608f20b04746c4b17569d7f11`。唯一私有目录是 `E:/edk2-samurai-out/charging-management-20261023/eud-bds-r2-private-01/`；本目录存在后拒重放。完整命令、源绑定、库成员、父快照、命名空间和产物 SHA 见 `result.json`，SHA `69241e6c22ea0daf10570a7745a30fdfab93f361073bb565cf22ecc3d5c66231`，公开与私有副本字节相同。

## 输入和实际命令

冻结 R2 源 SHA `c1ce63b3cc8df1c44b5351f53d15294505df919915fa8773636054305617cee8`。原平台静态库的代码成员确实只有 `PlatformBm.obj/`，另有 GNU ar 符号索引 `/`，没有其它代码成员。原成员与原缓存对象整文件相同。候选库仍只有这个代码成员，符号索引字节保持；归档成员的 SHA 与本轮编译对象相同。

使用原 `PlatformBootManagerLib/GNUmakefile:321,326` 和 `BdsDxe/GNUmakefile:404,412` 的真实四条命令；完整原行、变量展开后的 argv、工作目录与返回值保存在 child receipt。响应文件、库顺序、原 AutoGen/头文件及现有 GCC15 工具链直接复用。Make 中未定义的 `ARCHCC_FLAGS`/`SLINK_FLAGS` 按空值展开；`$@` 采用原 PlatformBm 对象目标路径。仅将工具名固定为已核实际工具的完整路径。未增加编译/链接优化选项。

先将源码目录、平台库模块 builddir、Bds 模块 builddir 各自完整复制到私有目录，逐文件核 SHA，再只替换私有源码副本中的 PlatformBm.c。child 使用 `unshare --mount --propagation private --fork`：自身 namespace `mnt:[4026532375]` 与 parent `mnt:[4026532211]` 不同，全部 mountinfo 无 shared/master/propagate_from，确认后才在 child bind 这三份私有副本到原规范路径。因此编译、归档和 GenFw 的绝对路径字符串保持；父命名空间不执行 bind、mount 或 umount。归档前按原 make 规则仅移除私有副本里的旧库，再以原 gcc-ar 命令创建新单成员库。

## 产物和边界

| 私有产物 | 字节数 | SHA256 |
| --- | ---: | --- |
| `PlatformBootManagerLib/OUTPUT/PlatformBm.obj` | 131944 | `7f86d1ccab2100fcf836e15b768f22cba40460a98984d1f5a4884c2bc99d7b0e` |
| `PlatformBootManagerLib/OUTPUT/PlatformBootManagerLib.lib` | 132222 | `89062b2351a516a3c0c7e66d32b7f4fae7b16686c047f90a34acab3837e5670c` |
| `BdsDxe/DEBUG/BdsDxe.dll`（ELF） | 1712712 | `556296de2d5f2882ff766b8a08fe40eb59c8ff8f06c2b340a8fb7d471fc66ed0` |
| `BdsDxe/OUTPUT/BdsDxe.efi` | 110592 | `a0e30c69b91f5605c07136f3f0c6900434f99d72159c5c61ac01db47fc061768` |

`original/` 保留原对象、库、ELF 和 EFI。四条实际命令均返回0；compile、archive、GenFw stderr 为空。链接保留原基线已有的 serial LTRANS 与 RWX LOAD segment 两类 warning，没有宣称零告警。

child 中对实际41库重新逐项哈希，仅平台库改变，其余40项逐字相同（包括 BdsDxe.lib）。父环境191个相关源、构建缓存、原41库、Makefile、EFI、编译依赖与工具的 SHA/size/mtime，以及目标目录 inode/device、namespace、完整 mountinfo 和目标 mount chain 前后全部相同。两个父快照 SHA 均为 `b18c8bc64cffc094794b8c1308c4de3197eeb3a4123e663dcfdf4942aa3c18d7`。

新 EFI 的静态 PE 检查确认 DOS/PE 签名、machine `0xaa64`、PE32+ `0x20b`、EFI boot-service driver subsystem11、4096对齐、可执行段内入口、段文件/内存边界及有界重定位目录；新 R2 日志标记和原规范 ELF 路径字符串存在。这是产物结构与构建源绑定检查，不代替 UEFI LoadImage、callback MMIO、真实 boot、EUD-off 路由或 USB500 的实机验收。候选尚未与 DTB 或任何最终固件组合，下一步由根会话决定。
