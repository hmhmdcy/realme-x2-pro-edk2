# Session71：原生S3706触摸实现及真机验收证据

本轮不止读取日志：GENI/GPI DMA/RMI4内建、本机触摸DTS/供电/复位补丁已实现、
构建并只部署boot/logdump。真机#61识别S3706A/fw3078696，F01/F12绑定，
用户操作后点按、移动、释放、多点输入通路通过。精度、严格物理触点数量、
休眠恢复/长期稳定性尚待验收。说明见sessions/71与NEXT-SESSION.md。

七份设备保存副本全部通过SHA256、gzip CRC和手机长度；16份原始capture包括
无回执F1、早期未同步reader和成功导出，原始数据保留，没有补字。关闭观察记录
与工具stdout/stderr一致；事件文件本身不含关闭行。最后COM14 Windows/Shared/
未Attached，三节点OK、无owner，Android/数据未改，EUD/init/core及回退保留。

主要文件：

- `touch-dmesg.validated.txt`：初始54413字节完整启动日志。
- `finish-dmesg.validated.txt`、`finish-facts.validated.txt`：操作后66932字节日志，
  新boot_id/#61/taint0、CPU频率/温度/UFS/UDC确认。
- `input-events.bin`、`touch-events-received.gz`、`input-validation.json`：306744字节
  实际input_event；12781记录，970帧，241个contact均释放，坐标在配置范围内。
- `touch-eventmeta.validated.txt`：手机事件原文长度/SHA及采样结束时中断计数。
- `touch-facts.validated.txt`：event2和RMI4/I²C driver链接。
- `baseline-bootmeta.validated.txt`：实际boot分区前缀与session68回退匹配。
- `firmware-validation.json`、`dtb-validation.json`：有效DT变化仅触摸接入，
  原有其余属性相同；UEFI除DTB/版本字符串外可执行字节相同。
- `config.diff`、`rmi_i2c.diff`、`samurai.diff`和source.gz：实际增量/原厂来源，
  可应用补丁另在linux-port/patches/0007与0008。
- `flash-validation.json`、`finish-state.json`、`source-preservation.json`：部署范围、
  收尾连接和不可变源码证据。

离线复核运行`python3 verify.py`；它独立验证归档内压缩副本、raw/text逐字节解帧、
DT语义、输入事件、不可变源码快照、收尾及SHA256SUMS，不访问手机。
`verify-firmware.py`是完整boot/FV解包校验器，重跑需要外部
`E:\edk2-samurai-out\kernel71`的boot/FD/FV大产物；这些没有放进Git。
本目录保留其原始JSON报告和构建/哈希记录，不以报告代替未做的硬件验收。
