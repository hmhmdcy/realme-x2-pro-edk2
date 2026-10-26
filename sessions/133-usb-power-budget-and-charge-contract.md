# 阶段133：USB输入预算与充电控制契约（2026-10-12）

当前仍是实际部署的内核#132和完整rootfs132。本轮没有新增内核或充电控制补丁。

本次启动读取MP2650两份12寄存器快照，全部一致。REG00/REG0F均0x12，按固定版本OEM定义为名义900mA输入限值；两节电池编码保持。USB处于configured/high-speed，MaxPower声明100mA、bmAttributes为0x80，Type-C端口数为0。声明不是供电端协商预算或电流测量，不能将现有900mA配置当作USB供电控制已完成。

当前132源码的PM8150B Type-C及VBUS regulator默认禁用，板级未覆盖；qcom_smbx尚无SMB5且CONFIG_CHARGER_QCOM_SMB2未启用。已找到[维护者SMB5 v4补丁](https://lkml.indiana.edu/hypermail/linux/kernel/2608.2/07902.html)，其内部充电路径和单节电压默认值不能直接套用于本机外置MP2650双节电池。下一步继续核对输入预算、热控与保护契约，成对输入限值写入需传播错误、回读和恢复验证。

纠正旧用语：0x2719是扩展电量计标识，不能称为“2719短路保护芯片”。精确型号/固件映射仍未证明，OEM独立短路保护路径是另一项。官方MP2650资料下载返回HTML挑战页，未取得可本地逐表核验的PDF，保留障碍并按可验证证据推进。

采集临时释放观测驱动并恢复同一OF client，用时0.030732秒，没有配置数据写入、强制地址访问或故障寄存器读取。原来源校验10秒超时发生在驱动恢复之后，保留部分日志；独立只读收尾成功，未重放I2C。24文件校验通过，NV6/来源4/vendor1及包数据库保持，桌面PID保持、taint0。GPU累计0/DPU4/蓝牙重组2与采集前一致，仅代表无负载观测窗口。

公开证据：reference/kernel133/source-inspection-validation.json、charge-control-contract-validation.json。原始资料与归档只在E:/edk2-samurai-out/kernel133及手机私有目录。采集和收尾脚本均已terminal，不重放；verify-contract-capture.py是只读校验。

GPU搜索已完成并再次核对[同平台作者记录](https://github.com/alexandr-mironov/poco-x3-pro-postmarketos/blob/main/README.md)和[Mesa文档](https://docs.mesa3d.org/drivers/freedreno.html)。同平台有同类CCU READ TRANSLATION，Phoc空纹理补丁只避免合成器崩溃；尚无本机验收有效的根因修复。131固定800x600单项硬件渲染通过，但退出约1.99及2.74秒后故障，整体GPU仍失败。禁止重放旧33场景。

15组功能边界与完整系统目标保持，充电控制与GPU均未验收。
