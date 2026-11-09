# 标准 ARM64 适配发布对照

更新日期：2026-11-09。本文只记录公开分支和它们的边界；真机状态以
[NEXT-SESSION](../../NEXT-SESSION.md) 和 [HARDWARE-STATUS](HARDWARE-STATUS.md)
为准。

## 正式标准分支

| 组件 | GitHub 仓库 | 分支 | 初始标准提交 | 内容 |
| --- | --- | --- | --- | --- |
| Linux 内核 | `hmhmdcy/realme-x2-pro-linux` | `codex/standard-arm64-v7.3.1` | `604f840ec52b24142aff59b5d1a77b6cecb58397` | Linux v7.3.1 上的 CAMSS/CCI/V4L2/PM8008 标准相机栈、四路 sensor 与镜头 glue |
| 用户态/设备包 | `hmhmdcy/realme-x2-pro-pmaports` | `codex/standard-arm64-settings` | `1e011d61a2ecf5b0eb77a75df3c71fa81aee8998` | `samurai-platform 5-r23`、`samurai-desktop 4-r11`、`samurai-camera-config r29` |
| 集成/文档/DTS/补丁 | `hmhmdcy/realme-x2-pro-edk2` | `codex/standard-arm64-v731` | `af70975e6974855a341d08c1f2bb4e3fb07265e2` | 标准 ARM64 文档、DTB 契约、内核补丁、构建/验证/刷写脚本和来源锁 |

集成分支的 `af70975e…` 是标准层起点；后续文档修正会出现在同一分支的
新提交中，以分支尖端为准。

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
- 物理按键冷启动、拔电冷启动、suspend/resume 和长期热/功耗仍未完成；
- 当前设备在 suspend 尝试后离线，需物理唤醒后才能继续；
- 真实 NFC 标签、外部 Bluetooth PAN/HID、指纹、SIM、高压充电仍待现场条件。
