# WSL 原 Ubuntu 恢复记录（2026-11-21）

## 现有发行版

- `Ubuntu`：原工作发行版，Ubuntu 26.04.1；VHDX 位于
  `C:\Users\cy122\AppData\Local\wsl\{ee461976-57ad-4560-8244-f266f2040781}\ext4.vhdx`。
- `SamuraiRecover`：11 月 19 日临时建立的 Ubuntu 24.04.3 恢复发行版，位于
  `E:\wsl-recover\SamuraiRecover`；已有后续构建工作，不能当作重复系统直接删除。

## 故障证据

- `wsl -d Ubuntu` 报
  `WslService/CreateInstance/MountDisk/HCS/ERROR_FILE_CORRUPT`。
- 原 VHDX 大小 231,947,108,352 字节，文件属性为稀疏文件。
- `qemu-img check --force-share` 返回 `No errors were found on the image`；`vhdiinfo`
  识别为动态 VHDX，虚拟大小 1 TiB，扇区 512 字节。可见不能简单断定 VHDX 文件
  本身已被截断；WSL 的严格挂载失败另有原因。
- `vhdimount` 可挂载原 VHDX，内核只读 ext4 挂载可浏览 `/home/cy122`；
  `samurai-dist-repo` 的 Git 状态可读。`e2fsck -fn` 报告多处 bitmap/checksum
  不一致，说明 ext4 元数据受损，不能承诺无损修复。
- Windows 在故障当天（11 月 19 日）多次报 C 盘空间不足；VHDX 最后写入时间为
  10:12:30，最后一次 ext4 挂载时间为 09:55:53。容量耗尽是可能的触发条件，
  但不是唯一可证原因。
- 精确的根因尚未由一次 reparative boot 证实。可重复的事实是：WSL 的
  `MountDisk` 调用报 `ERROR_FILE_CORRUPT`，而绕过 WSL 的 VHDX 只读路径能访问
  文件系统，同时 ext4 自身有真实的元数据校验和/位图异常。

## 已导出与校验

导出目录位于 `SamuraiRecover` 的
`/home/cy122/orig-Ubuntu-20261119`（约 33 GiB），包含：

- `samurai-dist-repo`（含 `.git` 和全部未提交修改，32 个状态条目与源逐字一致）
- `samurai-build`、`samurai-stable-repo`、`linux-samurai-github`
- `standard-arm64-v7.3.1`、`pmaports-samurai-userspace`
- `at2`、`aptest`、构建日志、内核补丁、模块压缩包
- `.ssh`、`.gnupg`、`.bash_history`、`.bashrc`、`.gitconfig`、`.git-credentials`
- `repo-patches/`：`samurai-stable-repo`、标准 ARM64、pmaports 等仓库的当前
  HEAD、状态、diff 和未跟踪文件清单。`linux-samurai-github` 工作树有大量删除
  标记，但 `git diff` 为空，说明树内容已缺失；需要从远端重新检出。

另有一份 **小空间修复覆盖层**：

- `E:\wsl-recover\wsl-ubuntu-fix.qcow2`（约 250 MiB）
- `E:\wsl-recover\wsl-ubuntu-fix.e2fsck-undo`（约 114 MiB）

该覆盖层以原 VHDX 为 backing file，修复后的 ext4 只读复核为 0；
原 VHDX 未被改写。用 `qemu-storage-daemon` + FUSE/loop 可继续只读挂载，
但覆盖层不是可直接启动的 WSL VHDX。详细记录见
`E:\wsl-recover\REPAIR-NO-FULL-COPY.md`。

原盘上 `steps/usr/lib`、`steps/usr/include/python3.14`、`steps/usr/include/KF6`
出现 `Structure needs cleaning`，未纳入导出。`rootfs-audit-20261119` 约 476 GB，
是可供重建的根文件系统审计生成物；不要为了“原样恢复”把它整体迁入
`SamuraiRecover`（新发行版的 VHDX 不能自动扩容到容纳整份旧主目录）。

## 安全操作

只读访问原盘：

```bash
sudo bash /mnt/e/RealmeX2Pro\ edk2/linux-port/scripts/wsl-recover-access.sh
```

导出脚本是 `wsl-recover-export.sh`。不要运行 `wsl --unregister Ubuntu`。
也不要在唯一的原 VHDX 上执行任何写入型修复：既包括 `e2fsck -fy`，也包括
会把它重新挂载为可写的 WSL 启动。请先复制，或使用经验证的只读/覆盖层路径。

## 未承诺的修复

原 Ubuntu 的 VHDX/ext4 还没有在副本上完成可验证修复。C 盘当时剩余空间不足以
安全制作 216 GiB 副本；E: 当前也只有约 98 GiB 可用，不够容纳整份 VHDX。
要恢复原发行版本身，应先准备至少约 220 GiB 可用的离线盘，复制 VHDX 后在副本
上执行 `e2fsck -fy`、只读校验和独立 `wsl --import` 启动测试，确认后才替换
原文件；不要在唯一原盘上直接运行 `e2fsck -fy`。
目前最可靠的结果是把未提交项目和相关数据迁移到 `SamuraiRecover`，原 VHDX
作为只读取证副本保留。

已在 `samurai-dist-repo` 上核对：原盘与新导出目录的 `HEAD` 均为
`0a02ba24c921e151e2edfc509c438382f4e4e574`，工作树状态均为 32 个条目；
DTB、补丁、模块包和 SSH 文件均可读并已计算哈希。
