# Session74：SM8150 DPU5命令显示接管（2026-10-10）

#68最终两次自动启动均无SMMU context fault、DSI错误、vblank WARNING或异常回溯，
taint0；每次三组彩条—白屏—彩条测试、九次显示关闭/开启，共18次通过。
原生SOFEF03F 1080×2400@60 DSC仍返回0x9c。GPU/GMU未启用。

## 问题、资料与实现

前一阶段#64首次显示接管有10条SMMU fault，IOVA0x9dxxxxxx在保留物理splash区域。
本轮先从同一手机取得新完整日志，随后核对实际Linux源码、2021/2022维护者原始
讨论与主线仓库，链接/适用代际在[research.md](../reference/kernel74/research.md)。
默认显示identity域会在msm IOMMU attach时换为paging域；本机遗留CTL0仍处于
command mode，LM图层非零、INTF_ACTIVE=0x2、DSC_ACTIVE=0x3，INTF1自动刷新仍开。

最终[0010补丁](../linux-port/patches/0010-drm-msm-sm8150-command-boot-handoff.patch)
将RM硬件对象初始化提前到IOMMU换域前，只在qcom,sm8150-dpu执行旧路径清理：

1. 停止INTF1外部TE/自动刷新；按旧VSYNC_INIT_VAL的高度，最多50ms等待旧帧结束。
2. 关闭tearcheck/旧command trigger；有界CTL复位，解除INTF/DSC/merge3d连接，清空LM。
3. 刷新/提交清理后的状态，再复位以取消等待已关闭TE的空kickoff，最后才切IOMMU域。

未更改SMMU匹配表或关闭IOMMU。EUD/RMI/RPMh、面板驱动、DTS、config、真实
init/USB hook均按先前SHA保存；本轮不改UEFI或boot。其它DPU、video-mode、
无缝保留splash与实际冷断电/休眠不在已验范围。七文件增量应用后与实际源逐字匹配，
checkpatch（忽略本地raw diff的提交消息元数据）0错误0警告，最终Image构建通过。

## 真机迭代与保留的失败

| 内核 | 实际结果 | 保留的证据 |
|---|---|---|
| #65 reset/clear/flush/start | 首次启动和九次显示循环通过，暖重启发生DSI下溢/vblank超时、taint512 | handoff-*、reboot-boot-dmesg、reboot-kms-first |
| #66去掉start | IOVA0 SMMU故障和DSI超时、taint512；没有稳定显示 | no-start-* |
| #67停TE、解除输出 | SMMU故障消失，首次接管DSI下溢持续；完整显示电源循环后恢复，CRC通过 | detach-* |
| #68等候旧帧+最后复位 | 两次自动启动及18次显示电源循环通过，taint0 | drain-*、final-* |

#65诊断full reprepare后vblank恢复，第一次CRC因未挂debugfs失败，也原样保存；
未把它算成功测试。#67初版构建使用了已不存在的intf_blks/to_dpu_hw_intf接口，
构建拒绝后改为真实rm->hw_intf；失败和修复日志均保留。
两次过早fastboot枚举与一次COM未启用的attach失败没有触发写入，后续工具增加
有界独立枚举等待。F1后的EIO对应设备离开Linux，必须结合真实F1和fastboot确认，
不能只看脚本退出码；六次F1均只有一帧OUT并有回执，资源finally释放。

## 最终验收

第一boot_id=904ec7b8-c9ef-4a00-8eda-be5535002262，第二/最终=2412cbe2-9f1d-4ea4-9c0b-8a19d4ff6568。
每次三组A/B/A、72个DPU CRC样本，合计144个；A=69961448/60af15f5、
B=25e11871/25e11871，A复现一致。每次九组60次vblank等待为约0.99秒，九次
完整panel disable/unprepare/prepare/enable与控制台恢复，共18次。两次日志各有
10次DCS电源读回0x9c；120/256/400亮度命令写入通过，软件属性不是亮度硬件读回。

最终56978字节dmesg、5493字节facts，以及本轮共22份设备导出，均按
设备打印SHA/gzip CRC/长度核对。[离线验证器](../reference/kernel74/verify-evidence.py)
同时检查失败候选、实际分区哈希、CRC/时序、六次F1、EUD和host释放状态。
Linux普通USB NCM/密钥SSH/SCP、S3706输入注册、六UFS、三个CPU调频policy和温度保留。
未重新做触摸人工多点/持续存储写入压力测试，旧功能数据流证据仍见sessions/71、72。
原生COM14命令K74_NATIVE_EUD_OK通过，两个data frame ACK、0重试；最终五个
相关PnP节点OK、Windows Shared/未Attached、连接owner为空。

## 部署、回退与下一项

本轮四次写入均为64MiB logdump，先校验当次F1、独立serial/product/分区大小与
镜像SHA；boot、Android、userdata/GPT保持。最终实际logdump SHA：
8e43d13658a1d332c441f68a6008e7ebb855177b59fbeb447a196195239f1ee5。
当前boot仍session73版本，前6680576字节SHA：
57508887131ae55cf9465fa1a44280fa45b507a3439345ffe635dc7544eaa999。
分区按PARTNAME查找，不猜sd编号；本次logdump=/dev/sde32、boot=/dev/sde11。
镜像/回退/源码变更前备份在本地kernel74；立即回退只需logdump-before.img（已验#64）。
大Image/镜像、GPU blob、测试二进制和私钥均不入Git。源码/证据只推fork/master。

GPU前置核对完成：本机七固件哈希通过，全zap ELF与b00/b01/b02及packed MDT内容
一致，relocatable LOAD footprint=4KiB，本机gpu_mem=8KiB足够。详情见
[gpu-loader-validation.json](../reference/kernel74/gpu-loader-validation.json)。布局匹配
主线MDT loader不代表PAS认证、GMU启动或GPU渲染成功；DT仍disabled，renderD128
本身不是GPU证据。下一项接入本机Adreno640/GMU并验证真实任务/渲染，再推进
电池/充电、无线/音频等14组功能。90Hz、冷断电、休眠、光学图像/亮度读回仍待验。
全硬件目标继续active，本轮属于有验证结果的阶段进展。
