# 207：补齐本机原厂 MCFG 文件服务与 TFTP 块号回绕

本轮修复并部署了两处文件服务问题：TFTP 大文件跨 16 位块号回绕，以及启动时缺失本机原厂 MCFG 目录。第二次普通启动已确认 173 个原厂 MCFG 文件自动复制到 RAM，基带请求的 `mdtime.txt` 能成功打开；GNSS 真实定位尚未通过。没有刷写分区，也没有修改原厂 NV、校准或备份。

## TFTP 协议修复

旧 writer 用线上 16 位块号计算窗口 ACK，绝对块 65539 的 ACK 错误；旧 reader 在绝对块 65537 错读。独立 QRTR 对照均复现。新实现内部保留绝对计数，仅在线上编码时截取 16 位；重复 DATA 与 ACK 按提交边界处理。真实 QRTR 完成 1,048,603 字节写入与逐字读回，跨两次回绕；14 次常规、窗口、范围、seek、截断、空文件及重复包事务共核对 26,580 字节，独立和正式服务均通过。[对照与回归](block-control-validation.json)、[正式部署](tftp-deployment-validation.json)

十份固定提交源码逐项校验、完整补丁无 fuzz 应用、Werror 静态构建通过。首次下载 TLS EOF 失败保留；随后用已验证的源码缓存在全新目录重建。第一次部署的路径核验在修改前失败，修正 `/usr/sbin` 符号链接的规范化比较后完成。[重建](tftp-build-validation.json)、[产品源码与构建入口](../../linux-port/radio/README.md)

## MCFG 启动目录

第一次普通新启动验证新 TFTP 与 32MiB RAM 工作缓存自动运行。`mcfg.tmp` 已能创建和读取，但仍为零字节；随后实际 modem 请求 `/readonly/firmware/image/modem_pr/mcfg/configs/mcfg_sw/mdtime.txt`，现有固件目录中没有该文件。[首次启动](runtime-validation.json)、[首次文件服务](bootstrap-validation.json)

只读核对本机 modem 分区：该子树实际有 173 个普通文件，共 8,807,671 字节，所需 `mdtime.txt` 为 12 字节。新增 `samurai-modem-configs.py` 在启动准备阶段将这些本机文件复制到私有 RAM，逐项校验后发布目录；它与临时 `mcfg.tmp` 分开，原厂文件不进入公开仓库。正式 QRTR 读回 12 字节与源一致。首次复制因 manifest 父目录权限不满足检查而在复制前停止，改用 0700 的 `mcfg-state` 子目录后通过。[清单核对](stock-mcfg-inventory-validation.json)、[同机 RAM 部署](mcfg-deployment-validation.json)

第二次普通启动使用新目录和独立 marker，前置身份、完整 quiesce 与私人归档通过；一次 RESTART2 后重新核对 fastboot 身份，发送一次普通 reboot，没有 flash。新 boot 已核对自动复制的所有 173 个文件；125.78 秒时实际 modem 已请求并打开 `mdtime.txt` 11 次，该目录打开错误为零，`mcfg.tmp` 仍为零字节。PDC 只读查询仍有活动平台/软件配置，无 pending；独立列表为 1 个平台、25 个软件配置，活动项均在列表且元数据查询成功。这没有证明整个配置流程或蜂窝业务完成。[第二次启动](reboot-r2/runtime-validation.json)、[实际文件请求](reboot-r2/bootstrap-validation.json)、[PDC列表](reboot-r2/query-pdc-details-validation.json)

第二次启动首次收集因等待 UTC 准备超过观察期限而失败，保留原失败。Wi-Fi 已连接时 chrony 仍未同步；对现有 NTP 来源发送 refresh/online/burst 后 chrony 正常，GNSS 服务自动完成 UTC 准备，共 19 次尝试。没有手动设置时钟、修改 NTP 配置或注入 GNSS UTC；也没有重新发送重启。本次不能算整个时钟链路完全无人介入通过。[时钟例外](reboot-r2/clock-readiness-validation.json)

## GNSS 接收与最终健康

本次启动首次 GNSS-only GeoClue 请求运行 181.37 秒，使用实际桌面 UID10000 和独立应用身份，其它定位来源关闭。收到 187 条不同 NMEA、174 个推进时间、10 条 GSV，校验错误零；自动一次下载与一次注入建立当前 168 小时辅助窗口。有效 GGA/RMC/raw fix、正 CNR、位置事件仍全为零。文件缺失修复尚未转化为真实接收改善。[接收收据](reboot-r2/geoclue-first-session-validation.json)

会话报告已恢复配置、关闭 GPS 并移除测试身份。首次最终检查在“GPS0 且 GeoClue 无 owner”的联合断言处失败，未确认当时是哪一项短暂不满足，原失败目录保留；独立观察随后为 GPS0、GeoClue 无 owner，但又出现晚到 Signals=true/rate0，保存后恢复 false/30。673.02 秒的独立最终检查确认三个 DSP running、taint 与五类故障均零，原 185 模块和配置保持，原厂 NV 保持，辅助窗口独立查询仍有效。这不是晚到状态竞态的修复。[晚到观察](reboot-r2/late-location-validation.json)、[最终健康](reboot-r2/final-health-validation.json)

两次 207 启动及前置测试共 290 份普通文件已私人归档并逐成员核对，原始 NMEA、设备身份、MCFG 清单与归档指纹不公开。[归档核对](reboot-r2/evidence-export-validation.json)、[源码闭合](source-final-validation.json)

## 当前部署与续作

TFTP 为 `b3bb82b9…`，Wi-Fi 启动脚本为 `854c9a8c…`，MCFG 复制程序为 `d4c62be6…`。当前运输与 boot guard 见 [NEXT-SESSION](../../NEXT-SESSION.md)；首轮和第二轮切换均已发出，不能重放旧 marker。TFTP 原件在手机 `/var/lib/samurai/k207-tftp-deploy/`，MCFG 部署前启动脚本在 `k207-mcfg-deploy-r2/`。回退前按当前身份、服务环境和文件所有权核对。

内核仍为 Image183/boot204，原 185 蓝牙模块和 MM191/helper421/init54 保持。真实 GNSS fix/CNR、配置初始化、RF/LNA/时钟、户外接收与精度仍开放；摄像头常态 sensor 图和冷启、真实蜂窝业务、传感器精度/SSR、BT 启动错误、Wi-Fi/USB PM、充电及其它外设继续属于完整目标。相关机型的具体方法和局限见 [realme/一加/OPPO GNSS 对照](../kernel205/GNSS-RELATED-DEVICES.md)。
