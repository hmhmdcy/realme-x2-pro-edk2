# 阶段97：自动本机地址供应与双频启动回归

已部署Linux #96，结果见[session97](../../sessions/97-automatic-radio-addresses-and-boot-regression.md)。内核驱动源码、配置、DTB、init和三个BT模块保持阶段96字节；CPIO仅修改Wi-Fi/BT服务并增加无线地址服务及两个静态工具。复用boot，只刷logdump。完整备份、包装审计、部署读回和131文件私人checkpoint校验通过。

本次暖启动在手动测试前已自动应用正确WLAN/BT地址。Wi-Fi在接口关闭时设置，活动接口地址冲突则拒绝。BT通过MGMT设置public address并重查正常索引，核对280字节READ_INFO，保持powered/connectable/discoverable/bondable关闭，不包含配对/连接。目录0700、身份文件0600且仅RAM；不写原NV/persist，不打印身份。热点连接仍通过私人RAM配置测试，自动本机地址供应不等于自动热点连接。

`samurai-radio-address`当前共同缓存要求WLAN和BT两个查询均成功，是待拆分的依赖；不能宣称首次WLAN/MPSS失败时BT身份独立。阶段96的MPSS停止时扫描证明此前RAM地址可复用，尚无全新离线身份来源。启动隔离/实际结束记录、幂等启停和锁保留。

2.4/5GHz认证、DHCP、网关、DNS、HTTP、双向各4MiB和后续各90秒/45样本扫描共存通过，公网ICMP失败。首次2.4GHz共存仅两个样本后出现reason7掉线并自动重连，随后key操作-110和三次显示frame-done timeout，关联原因未解决。后续窗口没有新增显示超时，vsync增长、underrun0；不能覆盖首次失败。本次BT有4次Frame reassembly -84、波特率重试0。蓝牙仅扫描，最终关闭接入/配对标志和电源；没有配对/连接。NFC本轮未重测，保留阶段96控制器证据。

| 文件组 | 用途 |
|---|---|
| `dms-mac-read.c`、`samurai-bt-address.c`、`samurai-radio-address` | 本机只读地址查询、MGMT供应和私人RAM缓存 |
| `samurai-wifi`、`samurai-bluetooth` | 已部署服务增量 |
| `build-address-tools.py`、`prepare-and-build.py`、`audit-kernel.py` | 对实际基线构建、CPIO/配置/DTB审计；历史输出存在时拒绝重放 |
| `test-runtime-addresses.sh`、`finish-runtime-addresses.sh`、`verify-runtime.py` | 刷前RAM失败/重试生命周期记录与校验 |
| `collect-preflash.sh`、`recover-backup-tail.py`、`repack-preflash-manifest.sh`、`prepare-package.py` | 完整备份、末尾传输恢复、清单修正及FAT候选审计 |
| `flash-connectivity.ps1`、`reboot-f1.ps1`、`read-eud.ps1`、`stop-connectivity.sh`、`scp-private.ps1` | 受控停止、F1、独立fastboot核对、限速SCP和reader释放 |
| `test-boot-and-connect.sh`、`observe-wifi-only.sh`、`coexistence-test.sh`、`verify-network.sh`、`start-five-ghz.sh` | 启动前手动调用前取证、BT关闭对照、双频/扫描验证 |
| `start-traffic.sh`、`wifi-traffic-server.c`、`wifi-traffic-client.ps1` | 双向4MiB数据及文件SHA校验 |
| `collect-checkpoint.sh`、`verify-checkpoint.py` | 保存原失败和完成阶段，验证清单覆盖/部署/数据/实际故障计数 |

其它`prepare-*.py`是本轮辅助生成器，不是通用自动部署入口。使用全新现场、boot ID和输出前缀；历史脚本的固定构建/分区/路径不能盲跑。首次READ_INFO长度误判、SCP尾部中断、根清单覆盖错误、首次共存掉线和5GHz检查调度过早均保留私人记录。

只公开自有代码和脱敏说明；二进制、固件、镜像、原日志、身份/凭据/密钥在私人`E:/edk2-samurai-out/kernel97`。原Android、userdata、GPT、NV/persist及历史显示快照保留。另一线程rootfs/F2FS不改，充电阶段不恢复旧探针或写配置。全硬件goal仍active；下一步见[交接](next-session.md)。
