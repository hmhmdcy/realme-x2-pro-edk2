# 206：修复 modem 工作文件服务，继续 GNSS 实测

本轮补齐了TFTP工作文件的RAM读写，已经安装到手机并完成真实QRTR传输；**GNSS仍未取得有效fix或正CNR。** 没有重启手机或modem、没有刷分区。本机仍是205第二次启动、boot204/kernel183。

## 发现与修改

PDC只读查询确认已有活动的平台/软件配置，均无pending；列表中有1个平台配置和25个软件配置，活动ID均在列表内，活动配置元数据查询成功。因此不能把本机简化为“完全没有MCFG”。旧qmicli列软件配置时返回InvalidQosId，独立GI查询仍能取得列表和活动项；该CLI错误不作为配置缺失证据。[选中状态](query-pdc-readonly-validation.json)、[列表与元数据](query-pdc-details-validation.json)

现有TFTP日志实际出现`/readwrite/mcfg.tmp`读写被EACCES拒绝，旧翻译器只允许`server_check.txt`写入memfd。新[RAM翻译器](../../linux-port/radio/samurai-tftp-ram.c)在32MiB独立tmpfs中提供工作文件、子目录、截断与续写；单文件限8MiB，固件四条只读路径保留，不写NV或原厂备份。顺带修复旧reader把省略rsize当成零限额、短包结束处理，以及writer未应用seek的问题。[完整上游补丁](../../linux-port/radio/tqftpserv-work-files.patch)

`samurai-wifi`启动脚本已加入私有tmpfs准备与服务环境，RAM缓存随重启丢弃。当前只重启了TFTP，RMTFS与MM保持原进程，modem未重启；因此原启动阶段的MCFG请求尚未重放，不能宣称真实MCFG初始化已修复。[部署](deploy-tftp-ram-validation.json)

## 验证

- 主机ASan/UBSan检查了RAM读写、缺失文件errno、截断/续写、路径/符号链接/硬链接/文件类型和固件保持。首次错误假定WSL的`/tmp`不是tmpfs，原失败保留，随后改用实测非tmpfs目录，主机与ARM64检查均通过。
- 手机上保留原服务，在独立QRTR实例206运行候选：原实例拒绝测试写入；候选完成13次真实事务，逐字比较20,435字节，覆盖跨窗口、整块边界、无选项传输、范围读取、seek、短文件覆盖、空文件与固件写拒绝。结束关闭测试实例、卸载测试挂载。[独立验证](test-tftp-isolated-validation.json)
- 替换生产实例后，同组13次/20,435字节验证再次通过，临时协议文件移除，NV源校验保持，故障增量0。[生产验证](deploy-tftp-ram-validation.json)
- 10个固定提交的公开源文件逐项校验、无fuzz应用完整补丁、Werror静态构建无告警；全新下载构建的二进制与已安装程序逐字一致。首次完整构建遗漏`ns.h`，失败目录保留，补齐依赖后通过。[重建](tftp-clean-rebuild-validation.json)、[可复现入口](../../linux-port/radio/build-tftp.py)

上述不是完整TFTP协议验收；跨65535块、异常重传和长期服务生命周期仍需补测。

## GNSS与最终实机

同一boot首次GNSS-only桌面请求运行182.35秒，UID10000、独立DesktopId，关闭其它定位来源：188条不同NMEA、176个推进时间、9条GSV，校验错误0；自动一次下载/注入使辅助数据从空窗口变为当前168小时。有效GGA/RMC/raw、正CNR与位置事件仍全0。[接收测试](geoclue-first-session-validation.json)

2590.67秒独立有效期查询再次确认当前有效；GPS0、桌面测试身份和配置已移除，三个DSP running，taint及五类内核故障均0。此前已知的晚到Signals=true/刷新0再次出现，原状态保存后恢复false/30，不能写成始终未变。[最终健康](final-health-validation.json)

205临时蓝牙诊断模块、启动脚本和BlueZ策略已全部恢复，185模块及loaded build-id、784个模块文件和配对key核对通过；主机hci_qca原源与原未剥离模块也已恢复。205诊断/trace和失败的GENI harness日志保留，没有形成GENI功能修复。[手机恢复](restore-bluetooth-baseline-validation.json)、[源码恢复](bluetooth-source-restore-validation.json)

205的259份、206的100份原生文件已分别私人归档，每个普通成员及归档校验通过，公开收据不含私人归档指纹。[归档](evidence-export-validation.json)

## 当前部署与下一步

TFTP程序`d0906a5a…`、启动脚本`ffb65d31…`，原件保存在手机`/var/lib/samurai/k206-tftp-deploy/`。回退应在当前身份、GNSS空闲及服务PID核对后仅替换TFTP/helper并恢复该目录保存的服务环境，不需重启MPSS或重注入辅助数据。当前没有未完成的测试worker或待确认重启。

下一步补协议边界并执行一次正常新启动，确认真实`mcfg.tmp`写入/读取、PDC状态和GNSS接收表现；随后继续本机RF/LNA/时钟与原厂定位初始化差异。新服务尚未形成APK，离线rootfs132未整合，不能把当前boot镜像当作完整发行镜像。摄像头常态sensor图/PLDO冷启、真实蜂窝业务、传感器物理精度/FastRPC SSR、BT启动错误及Wi-Fi/USB稳定性继续属于完整goal。
