# 37. 搜索原生多字节 RX 修复：源码差异与 PHY 生命周期（2026-10-09）

用户要求继续搜索如何修复原生多字节 RX。结论：**未找到能直接套用、已验证有效的修复**。
本轮取得同机型官方源码、更新的厂商实现及 2026-09-29 的 PHY 系列；具体行号、来源与限制统一见
[reference/rx37/README.md](../reference/rx37/README.md)，文件哈希见该目录 manifest。

## 37.1 状态与操作范围

重新只读检查 Windows：9501 和 9505 均 Status OK，9505 为 COM14；usbipd 6-5 Shared、没有 Attached，6-1 Not shared。
没有打开串口、发送数据、重置/重新枚举、构建或刷机；没有本轮 Linux 存活/运行时 PHY 状态的新回执。
上轮 Linux/COM14 回执是 session 36 的证据。临时终端、F1、tty/console 与 rx33-console 镜像均保留。
WSL 与 Windows 内核 eud.c 的 SHA-256 均为 `311e5508fccb8d6f0623ba21e7f5891e4fda45984ba9dd6c3a76168037c6d411`。

## 37.2 本轮真正增加和更正的结论

1. Realme X2 Pro 原厂 RX 仍是 ID/LEN/连读 DAT。该代码缺少本机所需 mask，还有 uart_add_one_port 成功判断反向的问题，不能视为实测成功的对照。
   当前驱动已处理这两点，不能把它们包装成新的本机修复。
2. 较新 SM8850 厂商实现也没有新增 RX 推进动作；其他 SoC 的 secure/TCSR/UTMI 配置不能直接搬来。
3. 更正 session 33：QUIC 覆盖 opcode 的 bug 位于三参数版本，COM timeout 调用正确的两参数版本。
   旧记录已标明更正；原始帧路径不受该 bug 影响。官方 COM issue 是旧线索复核，不是新发现的修复。
4. 新 PHY 系列明确要求 EUD 独立管理 PHY。本地 COM 驱动没有这个管理，旧启动记录又有 USB/PHY probe 延迟。
   这提供初始化方向，尚不能解释首字节成功而后续失败；没有证据把它定为根因。

## 37.3 下一轮怎样取得能区分原因的新证据

先用现有临时终端或已有日志核实当前 HS PHY 88e2000、QMP PHY 88e8000、DWC3 的绑定/延迟状态及实际 cmdline。
终端命令仍须逐字符受理、finally 关闭；长命令如果没有完整回显和换行受理，不能当作已执行。
如果当前 PHY 供应者仍未就绪，先定位资源链；MTP 已启用 USB 节点，不能靠重复写 status=okay 解决。

在此基础上才评估一个单独的 PHY 接管实验：只使用 DT 已知资源和 PHY API，先审清 reset 对现有 EUD 连接的影响及恢复顺序。
后续 session 38 已确认实际 HS PHY 匹配 SNPS femto-v2；session 37 的 QUSB2 参考不是本机匹配驱动，已更正参考说明。
保留当前 console/F1，不盲写其他 SoC 地址；若必须测试新内核，只替换 logdump，按既定飞轮手动小步进行。
正确结果仍要求 ABC=41 42 43、DEFG=44 45 46 47，并能复测。

若 PHY 状态无法解释故障，下一种有区分力的对照是 Linux 接管前的最小 UEFI RX 读取：同一已受理帧、先缓存后输出、与 Linux 共用原始 OUT 证据。
它能区分 Linux 接管阶段与更早的 COM/固件/共同 USB 路径，不能先验排除硬件或未公开固件。
本轮只记录该设计，没有实现或上机；没有再跑已失败的 burst、延时、readb、mask、nGnRnE、填充实验。

仍缺 SM8150 COM 专属的 FIFO read-pointer/完成文档或同 SoC 多字节成功对照。
不要把 SWD 限制、公开代码存在、USB URB 成功或 PHY 补丁标题当成 COM 已修复。
