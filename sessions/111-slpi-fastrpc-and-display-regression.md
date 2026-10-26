# 111：本机 SLPI、FastRPC 与显示回归

日期：2026-10-11。此阶段是历史记录；当前进展见[阶段112](112-startup-sensor-registry-and-reboot.md)。

从已安装 Phosh 的 userdata F2FS 系统继续，独立建立 kernel111 源码、初始化镜像和构建目录，保留109及原106来源。增加 SM8150 SLPI PAS、16 MiB CMA、FastRPC/SocInfo模块和本机 SLPI 固件路径；SLPI仍手动启动。FastRPC传感器PD采用上游的绕过SMMU参数修正，未全局关闭SMMU。pd-mapper补充SLPI传感器PD服务。

原厂本机固件、DSP库、注册表和配置以只读来源保存；未导入其他手机的固件或校准。内核模块及已安装的hexagonrpc/libssc包保持独立，未给传感器守护进程添加自启动。

最初独立EDK2构建出现多项非DTB差异，未刷入。实际候选以规范固件构建，仅改变内嵌DTB；候选与完整分区备份通过审计后，只刷boot和logdump，userdata不再擦除。规范EDK2工作目录和历史109产物随后恢复。

第一次111启动未进入持久桌面，用户确认出现不规律滚动花屏。诊断initramfs日志有taint512、显示错误和SLIM资源错误；128 KiB日志环不足，早期WARN已经丢失，不能据此归因。诊断USB/SSH恢复后，以ro,norecovery验证userdata身份和init、核验NV及本机来源，再卸载。

后续112保留111的boot固件和DTB，仅更新logdump中的内核与初始化镜像。完整候选、回退分区和原始诊断日志保存在私人目录，不能把111首次启动记为显示或传感器通过。

来源：[FastRPC传感器PD上游修正](https://lists.openwall.net/linux-kernel/2026/10/03/762)、[hexagonrpc](https://github.com/linux-msm/hexagonrpc)、[libssc](https://libssc.dylanvanassche.be/docs/)。
