# 当前目标（2026-11-12）

适配 RMX1931 的主线 Linux OTG：DWC3 dual-role、xHCI、标准
PM8150B Type-C/TCPM、`usb-c-connector`、`usb-role-switch` 和 VBUS
策略。私有代码只保留不可避免的板级层；禁止 GPIO10 extcon、
`keep-connect`、私有 ioctl 和 OOT 冒充验收；不写
NV/persist/calibration/userdata。

当前已通过：OTG Image/DTB 冷启动、NCM/MTP/Tethering/charging、
synthetic host/device、三轮标准 usb-moded host_mode、xHCI root
bus、Developer 自动恢复及 Windows DHCP/PnP。6-r6 已按 configfs
gadget generation 修复恢复预算竞态，签名 APK 已备。

未通过：物理 USB-C OTG hub/adapter、U 盘、键盘、反插、自动 TCPM
host、VBUS source、长期 host soak、同线 U3 host-resume。物理 OTG
不能由 synthetic 结果替代。

立即：设备在一次 30 秒 `rtcwake` 后于 Wi‑Fi/NCM 均不可达；先由现场
按电源键恢复，读取 `usb-otg-suspend.log`、`dmesg`、
`suspend_stats`、boot ID 和 `pm_wakeup_irq`。恢复访问后安装
`samurai-platform-6-r6.apk`，收集三轮 host-mode 原始日志，再继续
物理验收。真正 suspend 前先跑
`test-usb-otg-suspend.sh 30 --preflight-only`；不要在 preflight
失败或无人值守下重复 suspend 测试。通过后脚本会自后台化，SSH
立即返回，约 50 秒后重连读日志。
