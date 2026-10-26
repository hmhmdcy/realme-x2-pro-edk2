# 185：蓝牙功率脉冲解析修复、默认模块部署与PM

2026-10-15。仍kernel183/logdump183及boot/DTB172；本轮仅hci_uart同release模块覆盖185，无刷分区。实际QCA/H4代码1049主机场景与5负例通过，原模块扫描新增错误1、候选0；默认服务、热重启自动加载、开启无连接s2idle45.205秒/2392回调err0/QCA4及延后LE/BR/EDR/混合扫描通过。原组合在醒后2秒Wi-Fi5180检查失败仍保留，Wi-Fi随后自动恢复；既有密钥保持且未发起配对/连接。

完整修复、构建、回退、失败及私人证据路径见[185记录](../reference/kernel185/README.md)。[最终](../reference/kernel185/final-validation.json)是本次新boot；[当前检查点](../NEXT-SESSION.md)、[硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。传感器、GPS、实体camera、蜂窝业务及完整goal仍开放。
