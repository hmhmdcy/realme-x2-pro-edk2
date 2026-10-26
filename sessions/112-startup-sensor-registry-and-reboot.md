# 112：完整启动日志、传感器注册表与正常重启

日期：2026-10-11。全硬件goal仍active。已按用户授权将postmarketOS/Nura edge安装到userdata F2FS，用户选择Phosh；本阶段保留该系统。

当前部署内核112，boot固件与内嵌DTB来自111。本次仅刷logdump，不擦userdata。独立源码在`/home/cy122/pmos-samurai-kernel112`，日志环从128 KiB增至1 MiB；userdata发现等待由30秒增至300秒，身份、容量和只读验证条件保持。首次成功启动未实际超过旧等待时限，不能声称已证明300秒修改解决失败原因。

112首次进入Phosh，用户确认画面稳定、可解锁和打开应用；后续一次fastboot恢复启动也由用户确认稳定锁屏。完整日志有DPU帧完成超时，GPU故障未复现；旧滚动花屏和显示长期稳定仍未验收。主线触摸、硬件GLES2、NCM/密钥SSH、2.4GHz NM/Wi-Fi、HTTPS/NTP和桌面UCM继续工作。空闲PCM关闭、双功放静音、振动starts0的检查通过。音频声学质量尚未获得用户确认。

六个UFS LUN的geometry/head/tail共18项与111之前逐字节一致；boot匹配111，logdump匹配112；persist、6个NV来源、4个传感器来源保持。检查脚本见[布局核验](../reference/kernel112/verify-layout-after.py)和[检查点核验](../reference/kernel112/verify-checkpoints.py)，结果见[聚合记录](../reference/kernel112/checkpoint-validation.json)。原始日志、校准、凭据、录音、身份和镜像只在私人目录。

SLPI一次手动启动成功，出现SSC400服务、传感器PD与FastRPC节点，但加速度尚无样本。最初原生RPC试验缺少完整注册表父目录和OEM属性，DSP报I2C_ERROR_TRANSFER_TIMEOUT并崩溃；完整错误保留。SMEM135经只读外部模块取得100字节，本机Android R的ProjectInfoOCDT布局与旧结构不同；已按匹配的官方头文件和getter解码modemType。外部模块的正常OOT taint4096已随重启清除，模块卸载；不以错误旧布局值运行新试验。

RAM试验复制整个注册表父目录、vendor配置、本机DSP库和实际SoC/OEM属性，真实写入仅允许root所有、0700、tmpfs中的注册表副本，路径解析拒绝符号链接和越界。v1保留Android所有者导致安全拒绝，并暴露上游NULL根目录处理崩溃；修复后v2在同一启动的第二次SLPI启动握手超时，未运行查询。完整正常重启后的v3打开了RAM temp.json，但因监听器256字节接收限制退出，没有完成fwrite；加速度发现返回不可用。NV和来源均保持，SLPI收尾offline，taint0。

v4试验按Android公开FastRPC方法5补取大请求的剩余字节，限制单条请求最多4 MiB。实际监听函数的小请求、256字节边界、大请求完整回读及错误长度/传输失败/超限路径通过ASan/UBSan；真实RAM fwrite、append、flush及越界/只读拒绝测试通过。实机完成370字节请求补取，向RAM副本真实写入342字节，随后DSP仍报sns_com_port_i2c.c:227的I2C_ERROR_TRANSFER_TIMEOUT并崩溃。加速度查询254（事务超时），守护程序退出0不能视为通过；SLPI停止成功并保持offline，taint0，6个NV及4个来源保持。静态守护程序没有替换系统包或增加自启动；下一步核对本机总线、供电、时钟及固件资源。

一次直接正常reboot未恢复NCM，关机记录EFI运行时异常；后续F1回执有新内核时间，说明新内核已经启动，不能把该异常直接判为重置卡死。那次恢复只执行fastboot reboot，未刷分区，不能算正常重启通过。旧F1恢复脚本已封禁：上一启动的只读关机记录不能证明下一启动的根文件系统可安全复位。

随后使用完整关机流程停止Phosh/NM/WPA/BT/ath10k/MPSS、核验NV并同步，再由OpenRC重启；两次均核验独立新boot和taint0，试验后持久文件、Phosh/Wi-Fi/HTTPS/NTP/UCM空闲状态通过。EFI运行时异常仍出现，但新内核正常启动。用户确认两次重启和v4试验后画面稳定、解锁及应用正常；最新桌面快照有3次DPU帧完成超时、GPU故障0、taint0。不能把两次通过视为重启或显示长稳完成。

来源：[本机Android R内核](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source)（commit23172a1571bd91156032cc9fef16284a82b63d2c）、[hexagonrpc文件写入问题](https://github.com/linux-msm/hexagonrpc/issues/19)、[Android FastRPC方法5定义](https://android.googlesource.com/platform/external/fastrpc/+/refs/tags/android-12.1.0_r20/src/adsp_listener_stub.c)、[Android监听器补取流程](https://android.googlesource.com/platform/external/fastrpc/+/4f64577d37d5104a6f28fbe3b4ce0b5c2a7021eb/src/listener_android.c)。其他机型的资源试验仅供代码研究，不替换本机固件和校准。
