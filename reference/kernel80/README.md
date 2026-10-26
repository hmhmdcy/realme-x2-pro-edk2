# kernel80 证据

关联 sessions/80-gauge-identity-and-stock-cell-observations.md。
本輪只在session79运行环境进行有限的原厂查询，没有充电设置或分区写入。

- read-bq28-status.c：受身份保护的诊断原型；本机非2610时停止，完整status未执行。
- read-gauge-control-word.c：固定Control响应观察，无新命令。
- read-gauge-device-type.c / read-gauge-fw-version.c：固定原厂身份/固件查询。
- read-gauge-stock-cells.c：当场旧式FFA5门槛，固定原厂0071测量；两节4321mV。
- identity、legacy、paired-identity、firmware-version、stock-cells.txt：设备端原始响应。
- before/identity-after/final-dmesg.txt及final.gz：完整日志，设备端SHA核验。
- final-registers.txt / final-state.txt：MP2650一致性和标准电量计/DRM状态。
- collect-final.sh：固定boot/of_node/MP工具摘要，拒绝覆盖，保留原始日志。
- audit-observations.py / observation-validation.json：回显/长度/checksum、电芯总电压和保留摘要。
- audit-sources.py / charging-source-audit.json / source-references.json：固定原厂及官方资料来源。

扩展DeviceType2719尚未映射到确切型号/固件；旧式FFA5和原厂电芯接口匹配。
身份不同不能直接判断电池更换或真伪。保护状态/DAStatus2未查询，充电控制未验收。
O_RDONLY不能限制I2C_RDWR；R命令请求仍包含固定的I2C写帧。没有配置/NVM/解封/FET操作。
历史工具不可不经核对直接重放；适配器编号以of_node为准，目前gauge为/dev/i2c-2。
完整TI手册、可执行文件、镜像和身份文件均留在E:/edk2-samurai-out，不发布。

SHA256SUMS覆盖同目录所有文件（不含清单自身）；原始数据按字节保存，不修剪日志空白。
