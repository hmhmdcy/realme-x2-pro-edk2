# 当前目标（2026-11-09）

Wi‑Fi/NCM/SSH 已修复，仅保留为每次平台/内核变更后的强制回归门禁；
继续用 Linux v7.3.1 主线模型/API 适配其余硬件。

约束不变：无人值守优先；私有代码只留无法标准化的极薄板级层；禁止
私有 ioctl、Android/Binder 和 OOT 冒充验收；保留来源/哈希锁、可复现
签名包、推荐路线、成对 `boot`+`logdump` 和回退；不擦写
NV/persist/校准/userdata。

顺序：

1. PM8150L 闪光灯：DTB/boot/FAT 和 verifier 已过，待 fastboot 恢复后
   按 logdump→boot 成对刷入。
2. 私有 `status` sysfs 删除：Image `f8d89621…`/FAT `ca205192…`
   离线通过，未装机。
3. NFC：Alpine `neard 0.20`/OpenRC + 主线 `nxp-nci-i2c`；
   `samurai-platform 5-r22` 与探针已备，真实标签未验。
4. 蓝牙 PAN/HID：`samurai-bluetooth-host 0.1.0-r0` 仅含主线
   `bnep`/`uhid`/`uinput`；两构和隔离安装已过，autoload/外部对端/冷启动未验。
5. 其后：音频/PM/SSR、传感器、SIM、高压充电、显示与相机 userspace。

恢复设备后先读 `NEXT-SESSION.md`，确认 boot ID、`taint=0`、网络回归门禁
和分区回读，再单变量刷入。普通 `reboot` 不等于拔电冷启动。
