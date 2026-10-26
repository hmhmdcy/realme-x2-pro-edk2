# kernel78：相同镜像首次启动对照与无开关屏页面翻转

日期2026-10-10。详见 ../../sessions/78-first-boot-display-controls-and-pageflips.md。
三次相同镜像重启未重现DSI错误；第三次600次双缓冲翻转通过。间歇性故障仍开放。
没有内核/固件部署或分区写入，充电配置/NVM/快充MCU保持。

| 文件 | 用途 |
|---|---|
| hardware-validation.json、六份dmesg.txt/.gz | 设备端SHA、失败基线和三次成功启动、当前状态 |
| *kms.txt、*state.txt、*clocks.txt、kms-diff.json | 驱动自带debugfs的只读快照；跨启动差异不等于故障根因 |
| phy-binding-validation.json、display/handoff-functions.txt | 本机7nm/V4.0绑定及实际源码审查 |
| kms-refresh.c、refresh.txt、refresh-validation.json | 活动缓冲区重写探针；9个边界混合CRC保留 |
| kms-pageflip.c、pageflip.txt、pageflip-validation.json | 两个不变缓冲区、600个完成事件和CRC确认，无显式开关屏 |
| prepare/build/validate/collect脚本 | 可审查的诊断及离线核验过程，不含刷机 |
| reboot*.ps1、*-f1-wsl.events.jsonl、*-reboot.json、fastboot输出 | 一次F1发送及真实回执，独立枚举后仅reboot；前缀一次性保护 |
| final-device-state.txt、final-usbipd.txt | 当前#76、taint0、DSI0、gauge读数和USB owner释放 |
| SHA256SUMS | 证据封存，不应覆盖修改历史原始文件 |

大镜像、测试程序二进制、原始早期串口及SSH身份留在 E:\edk2-samurai-out\kernel78。
回退与充电研究仍看kernel77/76；本目录不包含新的“修复镜像”。
