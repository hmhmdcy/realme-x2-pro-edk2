# 374：绑定完成后原厂固件三项握手通过，停机阶段仍重启

本轮将临时诊断设备的资源绑定与固件启动分开。probe 只准备资源并返回；普通 platform bus 的 bound 通知、overlay apply 返回和用户空间持久化完成后，显式 sysfs run 才启动固件。SoC 核心仅增加 PING、PC_PREP 成功日志，硬件顺序沿用373。[补丁](post-bind-diagnostic.patch)。

**实机确认 SYS_INIT、SYS_PING、SYS_PC_PREP 均已应答，PC_PREP/WFI 返回0。** 日志顺序证实绑定已经完成，不能再把故障仅归于 probe 内启动。但在“A5 stopped, block reset asserted”之后、DMA退映射开始日志之前仍自动重启，run没有返回；没有完整清理或卸载终态。精确重启原因未明，不能仅凭最后一行认定因果。[实机证据](boot-runtime-r1-validation.json)。

原厂 ELF、完整日志和私有异常现场保留在私存；原厂 cam_hfi_disable_cpu 的正常路径只有PC/WFI、CONTROL、NSEC_RESET、INIT_REQUEST、IRQ操作，没有额外CAMCC全局块复位。下一步据此区分正常停机与失败强制复位，并核对DMA、时钟、电源释放。没有修改板级DT、主线设备链接框架、传感器或正式libcamera配置。

实际诊断owner 19条路径、worker分发9条和清理7条模型通过，提供者为桩；实际k363 in-tree两模块W=1/-Werror构建无诊断。[owner](owner-validation.json)、[分发](dispatch-validation.json)、[清理](worker-validation.json)、[构建](intree-build-validation.json)。维护提交`8bbd1f3d63e740dbf45918e785f763a9b9dde3be`，父373 `1e495f16...`；候选未永久安装。

重启后guard更新为k374-recovered，boot366/DT365和Image363读回保持；临时固件比对原厂及事务副本后删除，事务原件保留。桌面、音频服务、SSC及三remoteproc健康，CAMSS/双CCI休眠、taint0。[恢复](recovered-boot-validation.json)、[清理](recovery-cleanup-validation.json)、[健康](current-health-validation.json)。此次没有重新跑未改动的四摄采集；最新已完成的四摄与主摄隔离Gamma证据在373，不能冒称374重启后已验收。

完整HFI生命周期、IPE图像会话与libcamera后级接入、第五颗摄像头身份、更多模式及光学/几何/同步/连续AF仍待完成。整体目标保持active。后续375记录正常停机修正与实机结果。
