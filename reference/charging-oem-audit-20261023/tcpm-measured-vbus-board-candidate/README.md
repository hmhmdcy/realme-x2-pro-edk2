# PM8150B USB VBUS ADC5 板级候选

此离线候选仅为当前508设备树添加USB输入电压采样通道，并为Type-C控制器与MP2650 charger声明已有provider关系，供PD合同和5V start gate共用。它没有提高PDO或充电电流，也未生成或安装新Image。

## 板级匹配

508原始DTB中，Type-C控制器位于PM8150B的 typec@1500，ADC5 provider位于同一个 pmic@2/adc@3100。新增 ADC5_USB_IN_V_16（channel 8，prescale 1/16）并命名 usb_in_v_div_16；Type-C consumer通过 io-channels/io-channel-names = "vbus" 引用它，MP2650通过 typec-supply 引用Type-C provider。候选只改这3个属性。prepare-dtb.py 逐节点比较确认其余FDT内容完全相同，PDO和APSD配置未变。

- 原始DTB SHA-256：0ae7ade264e4d27c91861c2e87bb476f2237100f1d27ea8672cbbdba9f184f57
- 候选DTB SHA-256：b9ecb374bb7ba3ddb3490ee9da0ef948cb4c54303b4ed6759820a0aa6a2d6b14
- 变更：[measured-vbus.dtsi](measured-vbus.dtsi)、[DTB差异检查](dtb-result.json)

## 单位与限制

实际PMIC ADC5驱动的channel8 processed读值已经是微伏。以当前内核的实际缩放函数、PMIC全量程和1/16比例测试8个输入，结果通过；raw8670对应9,000,000µV。consumer必须直接使用 iio_read_channel_processed() 的数值，不能再乘1000。测试验证软件单位和缩放，不验证ADC物理精度、外部表误差、转换时间或板级偏差。

5V候选窗口4.75–5.50V只是待实机校准的工程门限，不是协议规范保证。后续须将电压读数与外部表在安全5V输入下对照，再验证事件时序；这份候选不授权提升输入电压或启用高压PDO。

- [实际ADC5函数测试](test-adc-units.py) · [测试结果](adc-unit-result.json)
- [DTB生成/精确差异脚本](prepare-dtb.py) · [原厂/上游来源索引](upstream-sources.json)
- 状态：未刷写、未启动新Image、未访问手机；等待与PD/APSD候选整合后再安排实机校准。
