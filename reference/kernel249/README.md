# 249：用户态仓库整合、独立复现与上游维护

2026-10-17，PC离线核验完成。没有连接、重启或刷写手机；物理手机当前OS未知。最后硬件验收保持240/247，248私人返回备份保留。

[pmaports默认分支](https://github.com/hmhmdcy/pmaports/tree/samurai-userspace)已发布，提交4aeae3b3035412794b2204e2f8bc104cef082a54。上游完整历史与固定基线保留，最终用户态差异整理为6个主题提交，samurai-bringup保留过程历史，两分支最终文件树一致，未强推旧分支。

| 项目 | 结果 |
|---|---|
| 公开源构建 | GitHub新clone、公开锁定pmbootstrap＋一个外置内核功能补丁；13目标配方和crossdirect成功，无旧私有SDK |
| 功能补丁 | libcamera最终6下游补丁＋原6发行版补丁；零fuzz、21源哈希、1490文件净比较通过 |
| 测试 | MM38项全部通过；RAM COW/sharedmem/TFTP/RPC四项ASan/UBSan回归通过，已知builder进程寿命分配不做leak验收 |
| 离线rootfs | 882包；189文件哈希、78ARM64 ELF、GI QMI、服务/用户配置通过；finalize重复执行通过 |
| 自备输入 | 同机SSC301文件、firmware160条目manifest通过，源备份RO；不公开固件/NV/校准/凭据 |
| 更新链 | 34个当前APK的签名仓库、来源标签、签名索引刷新与upgrade模拟通过；中间版本不进入候选仓库 |
| CI | [最终分支源检查成功](https://github.com/hmhmdcy/pmaports/actions/runs/38970573745) |
| 纯净维护内核 | 未完成；检查器按预期拒绝lab相机供电配置 |

新候选为libcamera r18/config-r13、Turnip26.2.4-r2、MM1.25.95_git20261005-r4；历史手机为libcamera r15/config-r10及958包。候选没有新实机验收，不能替代历史SHA或硬件结论。

公开GitHub可以复建用户态并说明最后状态；不能产生私人固件/校准，也尚未一键复建最后boot235/Image183/237模块与相机lab provider。滚动APK依赖和新签名密钥不保证历史位级一致。完整回退仍依赖个人248备份。

用户要求长期跟上游且补丁纯净。用户态已按原生包、功能队列与来源标签组织。内核分支04d4d4f9相对a90ee4305仍120文件差异，含临时OF fixture/overlay/phandle、诊断trace，235/237相机供电需正式化后才能移除。没有把改名或直接删配置当作完成。

- [重建文档](https://github.com/hmhmdcy/pmaports/blob/samurai-userspace/samurai/README.md)
- [完整核验边界与候选版本](https://github.com/hmhmdcy/pmaports/blob/samurai-userspace/samurai/REPRODUCIBILITY.md)
- [上游维护、内核清理清单与验收门槛](https://github.com/hmhmdcy/pmaports/blob/samurai-userspace/samurai/MAINTENANCE.md)
- [最后实机状态](https://github.com/hmhmdcy/pmaports/blob/samurai-userspace/samurai/STATUS.md)
- [248返回依据](../kernel248/STATUS.md)、[240交接](../kernel240/HANDOFF.md)、[当前检查点](../../NEXT-SESSION.md)

私人构建卷为D:/samurai249-build/build-ext4-private.img，WSL挂载/home/cy122/x2pro-linux/pmos249-build，收据/日志在E:/edk2-samurai-out/kernel249。原始私有输入、失败产物、缓存与日志均不进入功能补丁仓库。
