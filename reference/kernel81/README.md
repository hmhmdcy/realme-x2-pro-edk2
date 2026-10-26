# kernel81 证据

关联 sessions/81-stock-gauge-state-temperature-and-display-timeouts.md。
本轮手机保持session79 boot；用户确认电池从未更换。不从编号差异推断电池真伪。

- read-stock-gauge-state.c：复用80的QUP15/client/driver/lock/解析器，先核实FFA5/2719及
  精确FW负载，再只执行原厂0054和0057两项R请求。封存位=3、计量启用位=1。
- read-stock-temperatures.c：只读06/28/08/0c/14五个标准字；无MAC请求或配置数据写。
  电池温度3037(约30.6°C)，内部3025(约29.4°C)，不代表热敏接线/校准/保护已验收。
- stock-state.txt、stock-temperatures.txt、before/after-dmesg.txt：设备端原始读取及错误总线拒绝。
- collect-final.sh、final-registers/state/dmesg.txt及.gz、device-hashes.txt：3608秒状态；
  MP2650十二字段与79一致、taint0、DSI错误0，同时已有两次DRM frame-done timeout。
- inventory/extract-wifi-firmware.sh：固定PARTNAME、容量、UFS型号、boot_id、只读挂载及
  前后整分区摘要；vendor以ro,noload挂载，modem为vfat ro，已解除挂载。
- firmware-inventory.txt、wifi-extraction.txt、wifi-firmware-manifest.json：35项本机无线固件
  的私有归档和公开摘要/ELF元数据。没有安装、加载或无线验收，没有发布二进制。
- stock-dt-excerpt.json、source-audit.json、audit-sources.py：原厂充电接口、标准温度字、
  本机Wi-Fi供电和保留内存、主线及tqftpserv的固定版本依据。当前DT已继承正确四项供电。
- timeout-*.txt、probe-before/after-*.txt：两次既有超时后的当前KMS/DRM/时钟对照。
  这些是后续快照，不能冒充1545/1775秒故障发生瞬间的寄存器状态。
- run-after-timeouts.sh、pageflip-after-timeouts.txt、validate-pageflip.py：保存现场后的
  600次翻转/CRC复测；无显式CRTC disable或开关屏，超时计数2未增加。没有新光学验收。
- display-device-hashes.txt、audit-display.py、display-timeout-validation.json：原始显示摘要
  和旧session80日志追溯。此前检查遗漏这类超时，现已记录；没有修改封存的80原始文件。
- audit-observations.py、observation-validation.json：响应回显/长度/checksum、温度字、
  设备端摘要、Image/config/显示源保留及未验收边界。

0054/57请求含固定I2C写帧，只切换响应缓冲；O_RDONLY不自动限制I2C_RDWR。
完整80 status原型的2610门槛未放宽；0051/0053/0072未查询。没有解封、NVM/OTP、FET、
OTG、复位、快充MCU或充电配置写，没有手机分区写入、重启或自动开关屏。
所有新C读数工具用-Wall -Wextra -Werror -O2 -static构建，源/二进制摘要见validation。
本轮的固定路径/boot/工具摘要守卫是采集记录，不能不经核对直接重放。

SHA256SUMS覆盖同目录所有文件（不含清单自身），日志按原字节保存。
可执行文件、固件和完整手册在E:/edk2-samurai-out/kernel81或80，均未发布。
