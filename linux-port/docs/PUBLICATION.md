# 标准 ARM64 适配发布对照

更新日期：2026-11-14。本文只记录公开分支和它们的边界；真机状态以
[NEXT-SESSION](../../NEXT-SESSION.md) 和 [HARDWARE-STATUS](HARDWARE-STATUS.md)
为准。

## 正式标准分支

| 组件 | GitHub 仓库 | 分支 | 初始标准提交 | 内容 |
| --- | --- | --- | --- | --- |
| Linux 内核 | `hmhmdcy/realme-x2-pro-linux` | `stable`（源 `codex/standard-arm64-v7.3.1`） | `7fb2bdf254ba339cf5ce81fc2e316a6f8c8a5bba` | kernel #8 源码、完整 `samurai.config.kernel8`、`LOCALVERSION` 覆盖与复现说明；对应 Image `29c8d27c…` |
| 用户态/设备包 | `hmhmdcy/realme-x2-pro-pmaports` | `stable`（源 `codex/standard-arm64-settings`） | `0a02ba24c921e151e2edfc509c438382f4e4e574` | `samurai-platform 6-r18`、`samurai-desktop 4-r16`、`samurai-camera-config r28`、usb-signaller/unudhcpd 配方 |
| 集成/文档/DTS/补丁 | `hmhmdcy/realme-x2-pro-edk2` | `main`（标准起点 `codex/standard-arm64-v731`） | `af70975e6974855a341d08c1f2bb4e3fb07265e2` | 标准 ARM64 文档、DTB 契约、内核补丁、构建/验证/刷写脚本和来源锁 |

集成分支的 `af70975e…` 是标准层起点；后续文档修正会出现在同一分支的
新提交中，以分支尖端为准。

公开默认分支固定为 `stable`/`main`。`codex/*` 分支保留为开发/实验
分支，普通用户和发布 manifest 不应依赖移动的开发分支。

## 用户发布通道

普通用户不应 clone 开发分支或直接构建 `reference/` 证据树：

| 通道 | GitHub 仓库 | 内容 |
| --- | --- | --- |
| 系统发布 | `hmhmdcy/realme-x2-pro-releases` | boot/logdump/Image、772 模块归档、clean-rootfs 指引、安装/回滚说明、manifest、SHA256SUMS |
| 用户态 APK | `hmhmdcy/realme-x2-pro-apk` | 签名的 `packages.adb`、aarch64 APK、公钥 |

`realme-x2-pro-apk` 只更新用户态软件包，不更新 kernel、boot、DTB
或 rootfs。系统 release 和 APK release 必须按 manifest 中的
kernel release、module release 和索引哈希配对使用。

`logdump` 只含 `Image` 和 DTB，不含 `/lib/modules`。系统 release 的
模块归档必须是 `modules-7.3.1-rmx1931-samurai-v731-usbwake-otg.tar.gz`，
SHA-256 `5045c16b46928bc6ff9fbeb0418a21e34c12356954694665634c587006e19a02`。
不要把旧模块目录改名成新 release 目录；先解包到匹配目录并运行
`depmod -a`。

本项目不发布现成 rootfs。请按 pmaports `samurai/README.md` 从公开配方
构建干净 rootfs，并自备本机固件/校准。不要分发包含维护者
`/home`、`/root`、SSH host key、Wi-Fi 凭据或机器标识的 live rootfs。

## 设置边界

正式包只保留两类持久设置：

- postmarketOS/KDE 官方默认；
- 无法标准化的板级硬件接线、固件加载和标准 API glue。

调试用的 sleep lock、carrier-only guard、RTC suspend 测试、trace 和
抓包不进入正式包。详见 [SETTINGS-PROVENANCE](SETTINGS-PROVENANCE.md)。

## 历史分支

以下分支保留为历史 bring-up 记录，不是当前标准树：

- Linux：`samurai-bringup`、`samurai-camera-common` 及其它实验分支；
- pmaports：`samurai-bringup`、`samurai-userspace`；
- EDK2：`master` 中的旧 `Platform/Realme/sm8150/linux-port` 镜像。

不要用历史分支的私有 OF/驱动数量或旧 Phosh 配方判断当前标准层。

## 尚未随分支完成的事项

- 三个分支尚未在恢复后的同一启动周期内联合安装验收；
- 内核仍保留 `aw8697-samurai`、`max98937-samurai`、`samurai-audio`
  和 `samurai-sensor-power` 等板级薄驱动；它们尚未证明可以完全上游
  通用化，不能把这个分支描述成“零私有驱动”；
- 物理按键冷启动、拔电冷启动、suspend/resume 和长期热/功耗仍未完成；
- 当前设备在 suspend 尝试后离线，需物理唤醒后才能继续；
- 真实 NFC 标签、外部 Bluetooth PAN/HID、指纹、SIM、高压充电仍待现场条件。
