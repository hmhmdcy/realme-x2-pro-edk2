# 本机2719诊断查询：已完整实读并保持普通充电

2026-10-24。[实机查询结果](../../charging-management-20261023/protection-profile-live001-result.json)和[新组合待机结果](../../charging-management-20261023/protection-profile-pm001-result.json)已独立复核。当前Image504、USBebfcb、charger97c、保护f6bef、服务83469、manifest8c5b7，boot bf430d0d。未写boot/logdump，原481/468和桌面保持。

复用已构建的f6bef保护模块及其11组C/18解析案例；普通六命令、Health及共享锁/传输函数保持。服务只显式增加只读加载参数observed_2719_diagnostic=1。模块本身仍默认关闭；每次诊断先完整校验本批0001=2719，之后仅0056使用三字节profile，0050/0052仍四字节。不是按报文声称的任意长度自动接受。

独立冷启动后12项检查及fresh采用通过。新实例只执行一次capture：8个36字节报文回显、长度、checksum全部通过，批次108.905毫秒。0056实际payload3、length7、LE24值0x091810；前后真实BatteryStatus均0x0080，既有关键位掩码稳定。0050/0052/0051/0053为零，0054=0x386、0057=0x18。报告仍将兼容性、TCA分类和新充电/再充授权保持未验证；这批没有自然TCA事件。旧schema1/size4/-90及缺after0A的失败没有被改写。

新组合随后单次RTC实际驻留15.610秒，success+1/fail0，前后12项检查、原key/NCM自动恢复、500mA输入/250mA请求/8.725V帽、同实例已消费缓存均保持。8CPU trace无丢失/溢出，USB软件通知在complete中发布，alarm/trace已清。物理USB唤醒、温界、完整低电量/Full/再充、PD/厂商高功率仍待验。

部署工具复用原监督器与同子进程wait。三文件为保护模块0600、服务0755、manifest0600，正向81394/31400B，逆向eec61/29760B。正常流程、新manifest验证失败、第三文件rename失败三项实际stage/Unix文件测试通过，停充只允许原服务代码，读回和校验只加载两种已固定哈希的当前代码。单改回退恢复7848/61451/94a659并冷启动，USBebfcb和Image504/4453保持；不能套用更早的整套PM回退。

失败及恢复原件保留：r1包的服务权限问题在手机更新前发现；r2写入保护/服务后被旧只读回读身份检查拦住，未写manifest、未重启或查询，自动回退同样拒绝。核实终态、原驻留实例/同缓存/硬件INHIBIT后，独立恢复原三文件及健康Full保持；该事务没有重放。修正只读检查后，r3独立事务实际成功。PM启动回执沿用了旧guard_created标签；执行源码实际只重验既有guard，独立审计明确忽略该标签，原件不改写，后续模板已纠正。

私有当前目录protection-profile-update-live-20261024-03；r1/r2原件、明确恢复和逆向包保留。查询实例schema2/profile1、attempted=terminal=1，缓存SHA2f719089…8b7c02；不可重arm/重放。当前采用指针已更新，现有fresh-validation文件及旧guard保持。
