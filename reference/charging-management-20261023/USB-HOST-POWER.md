# SDP100与500申报失败：电脑端只读证据

500mA配置的单次软件重枚举没有得到主机native许可；60秒后原worker成功恢复100。不能把申报值当已允许电流，也不能绕过回调强制写高预算。原普通USB、充电250mA和电压上限保持，两个启动脚本已恢复100。

随后通过Windows SDK 10.0.26100.0的两项GET查询取得[电脑端证据](usb-host-hub-result.json)：内置05c6:9500 EUD集线器有7个端口，Windows返回HubIsBusPowered=true；当前只有端口1的05c6:9501 control，NCM未枚举。查询只打开零访问权限句柄，仅允许GET_NODE_INFORMATION和GET_NODE_CONNECTION_INFORMATION_EX，没有reset、cycle-port、设备重启、注册表写入或供电控制。接口名和完整节点原件留在私有host-usb-topology目录。

[Microsoft官方字段定义](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usbioctl/ns-usbioctl-_usb_hub_information)确认该布尔值表示总线供电；[节点结构定义](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usbioctl/ns-usbioctl-_usb_node_information)说明查询用途。实际布局及IOCTL号优先从本机SDK头读取，并记录头文件SHA。特别是usbioctl.h用户态结构处于pshpack1，连接状态偏移为31，不能按默认对齐误读成32。

这使“中间EUD hub的主机功率预算约束”成为合理候选原因，不能直接归咎电脑USB口不足，也不能宣称已证明500失败根因：失败发生时未记录hub端口ConnectionStatus/主机USB栈原因，现有终态不能补造当时证据。保持100回退，待手机恢复后先核实NCM真实父端口、EUD模式和相关缓存；若需下一轮申报实验，应同步记录主机端口状态，仍等待合法SET_CONFIGURATION回调，不能修改Windows供电规则来绕过约束。

该只读查询不证明手机已经唤醒或恢复。r5待机进程及RTC/PM trace仍待恢复连接后从原事务回收。
