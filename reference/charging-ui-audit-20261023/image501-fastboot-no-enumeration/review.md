# 原4126暖转fastboot但无USB：有限离线分析

根会话提供本轮现场事实：唯一 image501 事务已 prepare／quiesce／restart，用户确认 fastboot 屏幕；尚未写 boot／logdump，手机仍是原4126／ACA。主机原直连 root hub 仍在，手机原 port5 为 NoDeviceConnected／0000，其他键鼠／BT正常，目标 VID 和 fastboot devices 均无；同口物理拔10秒再接未恢复。本文没有新读手机或主机硬件，不将这些输入冒称本子任务采集。

**不能归为501失败，也不能已认定EUD/PHY根因。** 新Image及载体没有刷入。当前 NoDeviceConnected 比“未装 fastboot 驱动”更靠近物理连接／设备USB未拉起的层；尚无设备描述符，单换Windows驱动不足以解释或解决这个观察。

## 已有实际依据

- R7同Image过渡 `charging-management-20261023/r7-restart-state.json` 曾记录初始 EUD/NCM 全无、用户确认fastboot，后来fresh fastboot身份出现并仅reboot、零分区写。它证明这种表象出现过，不证明本次拔线应同样恢复。
- 固定source354 `eud.c` 619–620确实说明不退EUD会使主机看不到fastboot；旧 eud_reboot_cmd会退console、恢复AHB2PHY、关CSR后才kernel_restart。但本轮4126已实证COM disabled/unbound且无EUD主机拓扑，新 `eud-restart.py` SHA `5b9f309417342d297684e0e66766b0ba59e30dd68dfabd74c411a84875df727d` 只检查此状态、没有CSR写。不能直接沿用旧“漏退EUD”解释，更不能为了试探重新启用它。
- 与Image363逐字关联的 `apsd-integration/current-r7/snapshots`：DWC core的platform_driver（2920附近）和实际匹配的 dwc3-qcom-legacy driver 都只有probe/remove/PM，没有shutdown。固定 `kernel_restart_prepare()`只调用reboot notifiers和device_shutdown；platform bus仅在driver提供shutdown时调用它，**不会把remove当shutdown**。
- 同批femto PHY的 exit479–487才会assert PHY reset、关时钟和regulator；init386起会重新assert/deassert并初始化。所以上述暖重启通路**没有由这些driver回调保证**在交给bootloader前完成PHY exit／重初始化。平台machine_restart或固件是否另外复位这些域，此缓存没有充分证据；这只是具体的可能遗留点。

既有成功RESTART2记录多来自EUD仍由Linux持有、显式退EUD的旧环境；它们不能替代当前EUD常态off→ABL这次新条件的成功收据。没有找到“屏幕菜单 Restart bootloader 曾实际修好该故障”的已验证历史，不能假称菜单路径已验收。

## 最小恢复顺序建议

1. 保持零分区写。若当前**实际可见**菜单有 Restart bootloader，正常选一次，再由根只读核host port及fresh精确serial/product/两个分区尺寸。它是一个最小固件上下文重建尝试，不承诺清除所有PHY状态，不重复原Linux restart worker。
2. 若仍无枚举，菜单 START／正常启动原系统是下一条低改动路径：原4126与ACA尚在，无需刷任何回退镜像。恢复Linux后先核**新boot ID**、当前身份和原状态，原事务old-boot guard不能冒用到新boot。若需再次进入bootloader，应以新的受控事务与用户窗口进行。
3. 若正常启动也不能恢复连接，可从真实菜单正常关机、拔下USB、确认设备已关后再正常启动／进入既有启动选择。这样减少VBUS持续供电下旧连接状态的干扰，但不是已证明完整冷断电或必然修复。菜单无法使用时才沿既有官方恢复方法；不猜新的组合键，也不把强制重启当fastboot进入方法。

不建议现在增加CSR／AHB2PHY／PMIC写、手动解绑DWC／PHY、重复软件restart、切换新内核或刷回退。未知的ABL接手状态不能由“屏幕已fastboot”推断USB可用；只有fresh枚举身份才补足后续操作前提。

此结论只解释恢复次序与证据限制，不证明全局reset类型、ABL初始化错误、某个寄存器遗留或本次充电图标结果。

## 根会话随后提供的新恢复事实

用户实际选择 **Restart bootloader** 后，第一轮 fastboot devices 仍空，随后约几十秒出现唯一、精确匹配原私有序号的 fastboot 设备，主机枚举恢复。这是本轮新现场实证：**菜单正常重启bootloader之后恢复枚举，但不是立即恢复**。没有寄存器／固件trace，仍不把它归因于EUD或PHY，也不把等待秒数写成精确采集值。

根随后才开始唯一 flash-candidate 双载体操作，并等待原执行句柄；本说明没有查看或操作它，不证明刷写／reboot／新系统已完成。上文零写前提和恢复建议对应枚举缺失时点，不能用旧状态覆盖后续事务。今后同类故障可参考这一菜单恢复线索，仍须新鲜唯一身份与原动作终态，不能自动循环重启或重发刷写。
