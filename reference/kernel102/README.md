# kernel102：WCD934x与实际MAX98937识别

Linux #101已真实部署，codec/SLIMbus及API回复通过；实际双MAX98937 ID0x43已确认，错组件解绑/复位低，尚无ALSA卡。首次自动无线一次暖启动成功，5GHz网关3/3/DNS/HTTP通过；历史可靠性待办保持。

见[session102](../../sessions/102-wcd934x-and-real-max98937-identification.md)、[下一阶段](next-session.md)。125文件checkpoint `92fd414040265009df106e9a27236be6a7642ecc955f23f6211135cec13b51d8`，完整3原包/nested清单/运行FDT/读回/NV/persist通过。显示超时2，蓝牙关闭移除、无配对连接，振动确认暂缓。

本目录只含自写源、脚本、补丁和脱敏说明。stock contract/固定primary源码/provenance、prepare/build/audit、真实EDK2/package/backup/flash、runtime retry1、网络completion、精确haptics-device、ID-only GPIO/I2C诊断及checkpoint工具按阶段保存。签名固件、原DTBO/XML/库、原日志、身份/密码、镜像/二进制全部私人。

构建前与运行时guard错误原脚本/partial保留；已有目录不可重放。当前DTS保留最初MAX98927候选，但实际已解绑；下一轮先正确MAX98937驱动与DTS，不能直接启用机器声卡/扬声器。充电、rootfs01、Android/数据及原NV保持。

最终9文件只读现场在uptime 949.51秒确认同一次#101启动：5GHz COMPLETED、MPSS/ADSP running、fatal0、taint0，WCD组件仍绑定，错功放组件解绑/两reset低，BT控制器移除、振动standby/starts0、NV/persist不变；显示超时2/BT phase2错误2，无新增fatal。原包SHA `b48f30cb3c22efed6339597b658d22e14c5a813750f2023c3d29d666a3621728`，私人final-status-validation.json；全硬件goal保持active。
