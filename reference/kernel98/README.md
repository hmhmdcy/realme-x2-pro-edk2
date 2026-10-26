# 阶段98：独立地址供应与删除等待/脉冲诊断

Linux #97已部署，见[session98](../../sessions/98-independent-radio-identities-and-key-delete-trace.md)。独立WLAN/BT查询和缓存、故障注入隔离、手动调用前自动地址及跨暖启动一致性通过；热点仍用私人RAM配置，没有自动连接验收。新增过滤ath10k trace和hci_qca错误阶段诊断，key等待/UART时序保持。

双频网络和每方向4MiB SHA通过，当前5GHz；两次2.4GHz reason7掉线仍未解决，第二次BT关闭。45个COMPLETED采样漏过第一次掉线。三次单播删除约3.1秒-110且无确认，八次SET各有确认并返回0；未应用删除等待修复。三个BT错误均power-on pulse阶段单00字节，UART仍待修复。唯一显示超时早于Wi-Fi认证/扫描，不能归因扫描。BT仅扫描，13个地址/类型组合不等于设备数，最终电源和接入/配对标志关闭，未配对/连接；NFC保留阶段96控制器证据。

| 文件组 | 用途 |
|---|---|
| `samurai-radio-address`、`test-independent-addresses.sh`、`verify-address-isolation.py` | 各无线设备私人RAM缓存/锁、WLAN查询失败隔离和证据校验 |
| `prepare-driver-diagnostics.py`、`qca-rx-error-phase-diagnostics.patch` | UART错误阶段诊断，保留解析/时序/错误返回 |
| `prepare-and-build.py`、`finish-specific-build.py`、`audit-kernel.py` | 实际基线增量构建、三个BT目标、CPIO/配置/DTB/模块审计 |
| `capture-key-removal.sh`、`trace-reconnect-and-scan.sh`、`verify-trace.py` | 旧基线及新过滤trace/扫描/重连，明确掉线而非只看采样 |
| `bt-mgmt-probe.c`、`prepare-scan-probe.py` | 有界发现窗口和停止事件处理；本轮仅info/configure/off/scan |
| `collect-preflash.sh`、`prepare-package.py`、`flash-connectivity.ps1`、`stop-connectivity.sh` | 完整分区备份、候选包装、实际停止/枚举/部署 |
| `reboot-f1.ps1`、`read-eud.ps1`、`scp-private.ps1` | F1、reader释放、限速私人传输 |
| `test-automatic-addresses.sh`、`verify-automatic-addresses.py` | 手动调用前自动供应现场与同机地址一致性 |
| `verify-network.sh`、`start-traffic.sh`、`wifi-traffic-server.c`、`wifi-traffic-client.ps1`、`run-traffic.ps1`、`switch-band.sh` | 双频网络、启动监听器后立即双向传输和有界切换 |
| `collect-checkpoint.sh`、`verify-checkpoint.py` | 121文件含嵌套清单、部署读回/数据/真实故障计数验证 |

其它prepare工具是本轮生成器，不是通用部署入口。使用新现场/boot ID/目录，固定历史构建与设备守卫不能盲跑；扩大modules构建已按实际PID中止，特定目标retry1通过，初次编译/生成/校验/传输错误均保留私人原件。不能因捕获脚本返回0宣称稳定性修复。

CPIO只改地址服务和hci_uart.ko，CONFIG_ATH10K_TRACING n→y，debug_mask0；DTB/init/其它文件和模式/链接不变，btbcm/btqca沿用94。仅刷logdump，boot复用，完整备份/部署读回/121文件校验通过，六个原NV和persist不变。公开仅自有代码/patch/脱敏摘要；二进制/固件/镜像/原日志/地址/凭据/密钥留私人kernel98。rootfs另一线程和充电阶段边界保留，整体goal仍active，见[交接](next-session.md)。
