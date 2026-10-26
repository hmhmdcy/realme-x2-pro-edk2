# 201：GPS绝对有效期、自动UTC补时与标准GeoClue接入

旧XTRA窗口已经过期，标准新文件注入后窗口覆盖当前时间。部署按GPS启用触发的UTC/辅助检查服务，真实UID10000 GNSS-only GeoClue启停及自动worker通过；仍无fix/正CNR。受控旧文件注入Core.Aborted且窗口未变，没有将未建立的过期场景记成自动刷新通过。最终taint0、内核fault0，桌面设置/测试授权已恢复。

详见[201报告](../reference/kernel201/README.md)、[当前检查点](../NEXT-SESSION.md)、[完整硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。
