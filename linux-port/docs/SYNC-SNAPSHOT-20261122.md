# 2026-11-22 仓库同步快照

本页记录本轮 Windows/WSL 工作树向 GitHub 的同步结果。它只证明源码与
审计材料已进入远端，不代表重新构建、刷机或真机验收通过。

## 尖端

| 仓库 | 分支 | 提交 |
| --- | --- | --- |
| `realme-x2-pro-edk2` | `main` | `0abad66aa917820ffec208a2a6c1b1340a9ea7a3` |
| `realme-x2-pro-edk2` | `codex/board-packages-20261121` | `0abad66aa917820ffec208a2a6c1b1340a9ea7a3` |
| `realme-x2-pro-pmaports` | `codex/board-recipes-20261121` | `a9809cf4fc6f889a06fa741bae6a2b07f91de5f7` |
| `realme-x2-pro-pmaports` | `codex/standard-arm64-settings` | `a9809cf4fc6f889a06fa741bae6a2b07f91de5f7` |
| `realme-x2-pro-linux` | `codex/standard-arm64-v7.3.1` | `2b9ef80ba835861de72df39a230dd86fcb62563c` |
| `realme-x2-pro-linux` | `codex/standard-arm64-usbwake-20261121` | `2b9ef80ba835861de72df39a230dd86fcb62563c` |

本轮 edk2 新增 `ebcfc0e9`（Type-C wake、usb-signaller 与 USB 模式实验源码）
和 `0abad66a`（10 月充电审计修订、Type-C APSD measured-start 与 R8
power-supply 源码）。只收录可审计文本和脚本；未提交编译出的 `test-wake`、
`libssc.so`、Hexagon/radio-tools 可执行文件、日志、APK、模块或镜像。

## 稳定分支边界

- `realme-x2-pro-edk2` 的默认分支是 `main`，已同步到本轮尖端。
- `realme-x2-pro-pmaports` 的 `stable` 保持
  `0a02ba24c921e151e2edfc509c438382f4e4e574`；`main` 是上游通用分支。
  板级配方只在两个 `codex/*` 开发分支，不应把它当作已发布的稳定配方。
- `realme-x2-pro-linux` 的远端 `stable` 保持
  `7fb2bdf254ba339cf5ce81fc2e316a6f8c8a5bba`。标准的
  `codex/standard-arm64-v7.3.1` 与它没有直接共同祖先，不能合并或快进覆盖。
- `realme-x2-pro-releases` 仍为 `78e4dd2`，`realme-x2-pro-apk` 仍为
  `028e6b5`；本轮没有重新构建或发布 APK/rootfs 产物。

## 验证与遗留

- edk2 的 `main` 与开发分支在同一尖端触发了 `verify-scripts-and-packages`，
  两次 Actions 均为 `success`。
- pmaports 与内核仓库没有覆盖这两个开发分支的 CI 检查；“无检查”不是通过。
- 原 Windows 工作树仍保留构建输出、缓存和旧版本文件，未用其覆盖同步树。
  设备卡在 EDK2 的原因与 boot 分区 DTB 回归仍按
  [`BOOT-DTB-REGRESSION-20261121.md`](BOOT-DTB-REGRESSION-20261121.md)
  处理；先恢复 SSH 与 boot，再做其它适配。
