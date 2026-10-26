# kernel79 证据

关联sessions/79-mp2650-read-only-bus-and-current-settings.md。
2026-10-10，仅启用原厂QUP1总线，未绑定充电器；36次固定寄存器读取成功。
当前NTC和watchdog关闭、终止和12小时安全计时器开启；充电控制尚未验收。

- inspect-bus.py / bus-source-audit.json：原厂存档引脚与实际主线源码映射。
- prepare-bus.py / bus-dts.patch：基线备份和仅四项总线属性变更。
- build-dtb.sh / build-firmware.sh / prepare-build.py / verify-firmware.py：实际DT/FV构建与校验。
- dtb-validation.json / firmware-validation.json / candidate-validation.json：变更范围及保留哈希。
- read-mp2650.c：固定QUP1/0x5c，只读12个已知寄存器，排除REG14。
- mp-observation.txt / mp-followup.txt / observation-validation.json：三次实际返回及有边界的解码。
- first-state.txt：初次debugfs未挂载，空快照不是寄存器证据。
- mounted-kms.txt / mounted-drm-state.txt / mounted-clocks.txt：补挂后的原始状态。
- pageflip.txt / pageflip-validation.json：600翻转事件及完整缓冲CRC通过，无显式开关屏。
- before/first/mounted/complete-dmesg.txt及对应.gz：原始字节与设备端SHA对应。
- flash-bus.ps1 / reboot-f1.ps1 / bus-flash-validation.json：仅boot部署、F1一次回执和finally释放。
- first-passive*：COM14被动采集sent0，释放句柄；final-usbipd.txt：无WSL附着。
- final-state.txt：boot/logdump回读、taint0、DSI0；电量计/触摸总线已重新编号。
- github-realme-head.json / github-mainline-mp26-files.json：本轮gh API成功，固定源码核验。

封存后SHA256SUMS覆盖同目录文件（不包括清单自身）。脚本有固定基线与拒绝覆盖检查，
是本轮证据，不能不经调整直接重放。特别注意当前/dev/i2c-0是MP2650总线，
电量计为/dev/i2c-2；老脚本固定的总线编号已过时，应查of_node。
镜像、完整固件、可执行测试工具和密钥留在E:/edk2-samurai-out，不发布。

官方资料：
[MP2650 Rev1.0](https://www.monolithicpower.com/en/documentview/productdocument/index/version/2/document_type/Datasheet/lang/en/sku/MP2650GV/)、
[Realme固定源码](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/tree/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6)、
[主线固定目录](https://github.com/torvalds/linux/tree/3857c2fe5449541e24afc5efdb0f81a8a8f9a3a0/drivers/power/supply)。
Firecrawl开发者搜索可用但返回多种无关器件，未把它们当作MP2650证据；MPS旧URL间歇超时，
不含document_id的官方链接成功读取，未重发完整PDF。
