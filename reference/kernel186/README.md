# 186：SLPI停启、FastRPC共享池故障与本机A.11固件

2026-10-15。完整外设适配goal继续active，范围仍为GPS、实体摄像头、蓝牙、传感器、蜂窝等。本阶段不宣称传感器已经修复。当前仍kernel183/logdump183、boot/DTB172、runtime/modules132且仅hci_uart185覆盖，Mesa149/UCM173。边界见[WORKING-BOUNDARIES](../../WORKING-BOUNDARIES.md)。

## 原固件停启试验

重新核对185新boot，SLPI offline/供电0且本boot未启动，原hci_uart185保持。[准备](lifecycle-preparation.json)使用本机00121、原厂配置与校准的私有RAM副本、既有hexagonrpcd-v5；仅查询SSC属性，未请求测量流。文件服务保持运行直到DSP停止，再关闭服务、供电停5秒后仅尝试一次重新启动。

首次start、属性查询、DSP-first stop、第二次start均退出0，第二次状态running；第一轮完整属性只见wise_light/proximity等，accel/gyro实例仍为空。源码及NV核对保持。**第二次rproc启动成功不等于完整FastRPC/SSC重启成功**：随后FastRPC反复报SCM权限分配−22，末尾日志至少2259条SCM失败/2260条probe失败，kernel ring被覆盖。早期phase快照保留0秒日志与第二start之前的九项错误0，不能据此声称整个试验故障0。[实际范围](lifecycle-validation.json)

初始导出器错误地要求最终日志严格保留旧前缀，被真实ring覆盖拒绝；保留失败后改为分phase证据并显式标注缺口，不拼成不存在的连续全窗。属性data_type是数组，初次set转换失败也修正；查询类型有键不代表有SUID，必须检查非空实例。原始属性/日志均在私人包。

## FastRPC候选与实机失败

当前fastrpc.c在SDSP probe中把reserved pool从HLOS授权给DT VMIDs，但原remove及后续probe失败路径没有反向操作。原源码SHAa15e99ea…。[候选补丁](fastrpc-reserved-pool-lifecycle.patch)记录成功SCM调用返回的owner mask，在remove/失败unwind中申请归还HLOS；错误仍报告、失败时不清空元数据。现场DT VMIDs为3/5/6。当前[qcom_scm_assign_mem实现](https://github.com/torvalds/linux/blob/master/drivers/firmware/qcom/qcom_scm.c)也已本地核对：只在成功时更新srcvm，错误直接返回。元数据正确不证明调用时机正确。

实际probe/remove及helper提取测试337场景、ASan/UBSan、606次分配与释放；四个删除remove reclaim、删除probe unwind、错误时丢owner、错误时返回成功的负例均被运行时断言检出。[主机测试](fastrpc-host-tests-validation.json)。ARM64目标模块W=1告警0、同vermagic、import符号、原183/185源及Image/DTB/config保持，完整Module.symvers/modules.order恢复。[构建](fastrpc-module-build-validation.json)。初始checkpatch两处对齐检查及host stub两处误导缩进失败记录保留。

第一次受控热重启未刷分区，原驱动先启动。尝试临时unload/insmod被自动模块装载拦下：卸载后旧版立即出现，因此没有执行candidate insmod。原失败目录保持。随后将候选原子放入默认文件路径以供自动加载，已验证加载build-id与候选SHA95c9e2b0…匹配，taint0，旧4515b1b2…模块完整备份；当时只是under test。

三轮完整原固件文件服务/wise_light计划采用DSP-first cleanup并开启连续/dev/kmsg采集。**第一轮采样退出0，但stop时SCM归还权限−22，pool reclaim错误1，三轮总测试失败并立即停止，后两轮未执行**。[原样失败](candidate-runtime-failure-validation.json)。不能将主机绿灯当作TrustZone实际语义已验证。/dev/kmsg得到117记录、17167字节、EPIPE0、seq gaps0；按600秒边界自然结束，观察时进程已终止，没有凭ready文件重新启动采集。[采集范围](candidate-kmsg-validation.json)

原默认模块文件原子恢复，当前加载候选保留到受控复位，未强制卸载。维护内核fastrpc.c和原构建模块也恢复，失败源/模块/补丁另存，hci_qca185与原183的12源保持，最终仍tracked13。[源码恢复](source-restore-validation.json)。第二次受控热重启恢复实际加载的原FastRPC，未刷分区。源文件中的候选代码是失败原型，**不可把它作为已验收修复重新部署**。

## A.11离线提取完成

此前113阶段未完整下载的本机官方RMX1931_11.A.11，现在取得249个已核验区间，新增约45.4MB，保留113的失败与完整cache。所选firmware-update/modem.img压缩64611543字节，解压144011264字节，ZIP CRC449fd477通过，SHAe870086c…。[区间与CRC](a11-package-range-validation.json)

在独立Python3.14 venv中固定pycryptodome3.23.0；初始系统Crypto缺失、旧python3.12不存在两次失败保留。OZIP分帧仅按已固定MIT参考程序读取算法，未执行其脚本或包内updater。只读取相关ZIP member，并未下载/验收整个2.64GB包，不称全包已验签。

mcopy离线提取SLPI，版本SLPI.HY.2.1-00068-SM8150AZL-1（20190612）。22个程序头、20个加载段，split大小逐个与MDT匹配；同linked base、候选/原跨度均20MiB且fits，物理段布局不同。含LSM6DS3C/MMC5603/STK3331字符串只说明代码内容，不证明实际注册或采样。[布局与来源](a11-reference-validation.json)。**未向手机部署A.11，也未刷modem映像**；下一步仅在新启动、完整门控及独立路径下测试本机SLPI文件。

## 当前现场与后续

第二个新183启动已加载原FastRPC文件4515b1b2…，失败候选未加载；默认hci_uart185仍f6c5ed35…、build-id匹配。原BlueZ配置/密钥保持，蓝牙关/扫描关/连接0；Phosh/声卡、Wi-Fi5180、ADSP/modem running，SLPI offline/供电0且此新boot未启动。0秒日志、九类所列故障0，784树文件/770模块仅hci_uart1覆盖，boot/logdump/persist/NV/原来源核验。[恢复现场](restored-runtime-r2-validation.json)。不混入上一boot的采样、183历史音频SSR/声学/PM或185的PM证据。

两次RESTART2均根据当次新取boot身份、分区/模块核验、所有DSP/GUI/无线停止及F2FS冻结，只各发一次；分别观察新的fastboot身份/产品后各reboot一次，均无flash。所有私人包SHA验证，原始firmware、校准、密钥、trace、模块在E:/edk2-samurai-out/kernel186与手机k186*；只发布脱敏结果。

继续顺序：用原驱动及连续SCM入口/返回追踪核对owner mask、权限状态和rproc/glink/sysmon停机顺序，不能试遍未知owner或忽略−22；设计新的、实际能验证的生命周期修复。并在当前未启动过SLPI的boot测试A.11惯性注册/流，保持原固件/校准可回退。GPS真实fix/UTC/aiding/桌面桥、实体camera PM8008及CCI/C-PHY、蜂窝SIM/IPA与业务仍开放。相关同SoC仓库与官方源见[184研究](../kernel184/README.md)，它们的结果不替代本机证据。
