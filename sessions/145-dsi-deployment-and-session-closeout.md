# 阶段145：实际部署、启动追踪失败与本轮收尾

后续用户已撤销临时限制，当前仅保留[WORKING-BOUNDARIES](../WORKING-BOUNDARIES.md)中的四类边界。本记录的历史操作和测试结果保留，下一轮规则已同步更新。

2026-10-12 23:37（Asia/Shanghai）。按用户要求完成进展、文档和交接；本轮结束，不把完整适配目标标为完成。

阶段145已只刷logdump并实际启动，系统/模块仍为132；boot/logdump回读、实际设备树、770模块、GPT18、persist及NV/原厂来源校验通过。Phosh/Phoc存在、taint0，累计DPU0/DSI0/GPU0/WARN0/TXprepare9，显示空闲，未做GPU专项负载。启动追踪未取得结果，未确认启动链根因；失败证据已封存，本轮临时开机服务已移除，k145-startup实例不存在。显示、GPU和充电均未新增验收成功。本轮按用户要求收尾并交接，完整适配目标仍未完成。

## 已完成与证据边界

145包含144 EUD退出同步修复和新增的DSI原始状态追踪。DSI实际函数24项、EUD实际函数26项宿主测试通过；完整Image/modules/DTB构建、770模块与132逐字节一致、三个initramfs蓝牙模块及FAT只读校验通过。宿主模型不能替代实际时序或硬件验收。

145 Image为59243008字节，SHA256 `f38c7bf0da64ea39c97233ee981ca2d99df481fb5c1efe94ee9de3863f061163`；64MiB logdump SHA256 `515cd78719506bfaa801bbf312539c8bdef0a142c27531076a5b820e271b6999`。四件套使用boot132、logdump145、modules132、完整rootfs132；实际仅刷logdump，userdata没有全量重刷。独立新boot及运行时保护项已重新取证，不再使用旧140身份作为当前手机身份。

刷写前140停止流程出现70次TX prepare失败，原停止脚本已终态且没有重放。将那一次的完整故障前缀封存后，逐项核实设备已停止、taint0与受保护内容不变，才完成本次切换。该豁免仅绑定旧140/特定日志/特定切换，不能接受145运行错误或用于后续停止流程；70次失败中每一次的通道状态没有记录，不能宣称全部为NULL/DOWN或问题已修。

本次F1回执来自切换前140，主机实际收到后进入启动管理器。145包含144补丁，但145自身退出时的实机回执与panic仍未验证，不能把旧140回执算作该补丁的实机成功。

## 收尾时的实机状态

当前内核构建#145，release仍为`7.3.0-rc6-rmx1931-samurai-k132+`，software generation132。Phosh/Phoc均存在，DRM连接存在但CRTC inactive。taint0，累计DPU timeout0、DSI worker0、GPU fault0、kernel WARNING0、codec ENOSPC0、TX prepare9。最后的临时服务清理前后上述计数一致。空闲、无GPU专项负载和没有新增计数都不能证明显示/GPU稳定，TX prepare9也意味着尚未达到“无报错”。

boot132/logdump145实际分区SHA256、live DTB语义与132、GPT18、persist、NV6/source4/vendor1、784模块树记录（770个模块）和GUI三文件均通过。USB SSH/SCP可用。充电只读驱动仍存在；没有做新的充电控制/温度保护验收。当前Wi-Fi已关联、BlueZ服务启动，MPSS/ADSP运行，SLPI及传感器供电关闭；本轮未重验无线数据流量或其他硬件。原系统display/radio追踪实例仍开启，本次只清理k145临时记录器，没有关闭原系统观测。

## 启动追踪失败与临时服务清理

`k145-startup-trace`安装时三文件哈希正确，但新启动没有采集目录、PID文件、输出日志、样本、完成标记或归档，OpenRC状态为stopped。三个DSI追踪事件已在实机注册，当前采集失败不能归结为追踪点缺失。准确的启动链根因尚未确认，本轮不继续重启实验。

使用新的同boot守卫，确认无记录器进程、自建trace、PID文件与结果后，先封存安装源码、OpenRC状态、清理前日志和哈希，再只移除该临时boot链接和完全匹配的init服务。没有杀进程、重放完成-only stop、启动晚采集冒充早期采集或删除诊断源码。失败记录仍保留，GUI三文件不变，清理前后计数无新增。

公开证据在`reference/kernel145/first-runtime-validation.json`、`inactive-recorder-closeout-validation.json`及`dsi-observation-build-package-validation.json`；原始归档、boot ID及日志在私有`E:/edk2-samurai-out/kernel145`。当前身份以该目录`embedded-boot-id-private.txt`和手机`/var/lib/samurai/k145-first-runtime/boot-id-private.txt`为准。主机归档SHA256和内层清单均已核验。

## 后续可继续的工作

可以修复OpenRC启动追踪链并分析DSI/DPU时序，也可以通过GPU负载、映射事件和驱动候选继续定位迟发CCU故障，或推进充电控制与保护链。工作次序按实际线索选择，GPU测试、整套用例、debug、缓存与时序修改不再受原临时禁令限制。

旧脚本、采集器和工具可以复用或修改。刷写、重启和切换仍按当前设备状态执行，既有旧140停止故障和F1收据只证明当时的结果。普通读取和宿主分析不要求重复全量核验所有模块、NV和分区。

## 构建与清理恢复位置

当前源码/Image：WSL `/home/cy122/pmos-samurai-kernel136/kernel`；目录名136不是内核构建版本。新145模块安装树为同级`modules-root145`。私有145镜像、132四件套与140回退镜像均保留；需要回退时确认当前设备及分区状态。

E盘清理已完成：98个过时产物、8个重复ISO分片移除，5个旧卷完整zstd封存并解压流SHA/长度核验，净释放94.39GiB。该数字属于清理完成时的收据，不代表此刻剩余空间。118/122/126/129/134旧卷可按私有`cleanup145/cleanup-ledger-private.json`从封存恢复，也可为新工作重新构建。原C盘WSL、源码、日志和工厂/NV备份目前仍保留；重要备份不覆盖。

本轮没有提交、推送、发布或向其他会话发送交接。当前操作规则已由后续用户指示改为仅保留WORKING-BOUNDARIES.md的四类边界，其他临时禁令撤销。私人身份、地址、密钥、镜像和原始日志不写入公开文档。
