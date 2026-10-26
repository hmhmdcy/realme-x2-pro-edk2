# Image501 私有载体：已生成，未部署

三阶段均沿原唯一 exec 等待到真实 rc0：BDS session45236 / Linux PID502；boot session39335 / PID907；logdump session15675 / PID797。无手机、SSH、USB、SDK、Git、安装、刷写或重启；未重编 Image、模块或 DTB。

| 载体 | 私有输出 SHA256 | 字节数 |
| --- | --- | ---: |
| boot | `97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695` | 100663296 |
| logdump | `7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9` | 67108864 |

输出分别位于 `E:/edk2-samurai-out/charging-management-20261023/gauge-image501-{boot,logdump}-private-01/`。完整结果和真实 argv/log 留在各私有目录；本叶 `boot-result.json`、`logdump-result.json` 为有原件哈希绑定的简明收据。`result.json` 专指 BDS 构建收据，未被后续阶段覆盖。

源代码唯一差异为 `r2-to-501-LoadOptions.patch` 的一行：在冻结 R2 BDS UTF16命令行末尾追加 `bq27xxx_battery.samurai_instant_current=1`。实际 built-in 对象确认此前缀，EFI stub 的非空 LoadOptions 会覆盖运行时 chosen；因此原 native DTB9271完整保持，不修改内核 C 默认 false。BDS EFI 为 `071a628bd34c8d4715c0b57b89a219e21c236d2f5f16c8d82bd832de4dcc196b`，有效 ARM64 PE32+ 内含精确 UTF16 参数和原 EUD-off marker。

`run-bds.py` 仅复用原四条 cached compile/ar/link/GenFw 命令。私有复制原 R2 source、PlatformBootManagerLib、BdsDxe，无 hardlink；只在已证明不同且 private-propagation 的 child mount namespace 内覆盖三处 canonical path。只换平台库的 PlatformBm 单代码成员，其余40库保持；261个父输入和父挂载状态前后相同。原 link 的 serial-LTRANS/RWX 警告仍保留在 stderr，不将既有警告称为零诊断。未运行 make、AutoGen 或全固件构建。

`package-boot.py` 从实际4126提取101个完整FFS，只更换BDS；其余100完整FFS（含native DTB9271）逐字保持，BDS depex/UI保持、PE payload等于新EFI，不填充PE规避差异。SEC完整字节和0xfe8位置、144字节shim、compat、ramdisk及绝对tail均保持；沿已验证 pre-rebase SEC+sidecar/default GenFv 路径。gzip按原 `gzip -c`、regular fd0、原可复现mtime执行。新payload6680472B，newused6684672，等于当前4126边界，页内余104B；Android v1头仅kernel_size/ID变化，ID先验且写后重新完整解析。曾在只读check-local发现并修正原文件名替换误差；当时尚无新输出目录或工具执行，正式唯一封装未重放。

`package-logdump.py` 私有复制精确ACA，再用原mcopy替换/Image为已冻结的 Image501 `3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02`（59243008B）。实际mcopy读回逐字一致，`fsck.fat -n`通过并确认其未写。FAT16其它条目、DTB365内容和cluster链逐字保持；全部变化必须落在旧/新Image数据cluster、其目录slot或自身FAT16链entry，其余每字节保持，包括删除slot、label、slack和其它文件。原ACA、Image501、工具/源及父mountinfo均保持。

精确回退为 **boot4126 + ACA logdump（Image363）**，完整SHA和路径见 `delivery.json`。后续激活涉及boot/logdump两个独立分区，不具有硬件原子性；两个候选都确认写入成功前不能candidate reboot。部分/未知写入先核同进程终态，不重放，恢复两个原件并验证后才能reboot-original。不复用旧有状态事务。本叶没有激活/fastboot入口。

R8、rootfs、正常500脚本、相机481及现有模块/ABI不在写路径。Image501已有独立ABI收据；本轮只复用，不重跑。参数实际生效、电流方向与图标剩余延迟尚待后续受控启动采集，不能由离线载体推定已修好。
