# 240：相机应用故障、Snapshot CPU 预览与后摄统计

2026-10-16，阶段结论为 **progress**，完整Linux适配未完成。以下为240实测收尾记录：236启动、boot235及237的789项模块清单保持，libcamera r15/config-r10未改，新增Snapshot 51.0-r0及14项发行包依赖，并保存仅该应用的CPU显示配置。

文档交接时目标已为 **paused**；本次交接未新增手机操作或硬件验收。接手建议、脚本风险、证据路径和回退入口见[HANDOFF](HANDOFF.md)，当前状态以[根检查点](../../NEXT-SESSION.md)为准。本页实验方法描述240当轮条件，当前操作规则仅见[WORKING-BOUNDARIES](../../WORKING-BOUNDARIES.md)。

## 为什么桌面相机打不开或退出

默认Megapixels 2.1.0/libmegapixels 0.2.3缺少samurai机型配置，输出“No suitable config, defaulting to uvc”。该后端只接受`uvcvideo`，不会发现本机CAMSS；它自行配置V4L2/GL，没有使用已适配的libcamera r15。[本机检查](camera-app-audit-validation.json)。

匹配版本源码还存在可达的零相机退出路径：无pipeline时方向回调仍调用更新函数，后者打印`no pipeline`并`exit(1)`；切换空相机也有缺少空指针保护的问题。会话日志出现过`no pipeline`，但缺少对应用户操作的完整栈和时间，不能把每次退出都认定为这个触发点。[方向回调](https://gitlab.com/megapixels-org/Megapixels/-/blob/5fb1f24f1aeef80ea18224ab5829fda85653a4e8/src/main.c#L1299)、[退出位置](https://gitlab.com/megapixels-org/Megapixels/-/blob/5fb1f24f1aeef80ea18224ab5829fda85653a4e8/src/io_pipeline.c#L712)、[UVC fallback](https://gitlab.com/megapixels-org/libmegapixels/-/blob/d50bf166972df4252d127f72f90986892f3cd901/src/parse.c#L618)。

受控Megapixels启动[存活12秒](megapixels-startup-validation.json)，`-2`是诊断主动SIGINT收尾，不是复现的崩溃。SSH降权子进程的方向传感器claim被拒，不能代表用户在活动桌面的完整路径。单独升级libcamera或随意填写一个Megapixels配置不能完成这层适配。

## Snapshot 显示故障与已部署回退

Snapshot使用GStreamer/PipeWire接入libcamera，具有完整拍照/录像代码路径；本轮只验预览，没有触发快门。签名离线原生[安装](snapshot-install-validation.json)仅新增14包至958，原944项包记录及49个r15/r10载荷保持，移除Snapshot的原生模拟恰好移除14新增项。手机TLS下载失败已保留；主机HTTPS中继后仍由手机原可信密钥验签，没有替换发行包签名。

用户从Phosh打开的默认Vulkan会话出现`VK_ERROR_DEVICE_LOST`。对后续活动会话5秒观察得到10条新增GPU fault、没有有效缓冲trace；精确SIGTERM后所有相机设备恢复suspended。最终内核保留480条历史GPU fault，不能报告240全程fault0，也不将其混同旧CCU问题或211 GPU ISP退出告警。[观察](snapshot-existing-stream-validation.json)、[停止与恢复](snapshot-fault-stop-validation.json)。

CPU路径验证按失败推进，没有把窗口存活当作出图：

| 路径 | 真实结果 |
| --- | --- |
| Cairo且禁用DMA-BUF，首轮 | 窗口被桌面挂起，0帧；不能验收预览 |
| 用户确认解锁后，同样禁用DMA-BUF | 18个递增PTS缓冲；8个paintable Bus Error，提示DMA-BUF被禁；0次CPU映射 |
| Cairo，保留线性DMA-BUF，禁GL/Vulkan/offload | 765个递增PTS缓冲、324次1920×1080 XR24:0 CPU mmap、0个paintable Bus Error；163个缓冲回收错误仍开放 |
| 用户要求重试，30秒 | 1436个递增PTS缓冲、600次相同CPU mmap、0个paintable Bus Error；301个回收错误仍开放 |

[16秒证据](snapshot-mmap-frame-flow-validation.json)、[30秒重试](snapshot-mmap-r2-frame-flow-validation.json)。两次应用无`/dev/dri`设备FD、新增GPU fault/WARN/Oops为0，图、格式、控制、rails、PM和MCLK完整恢复。mmap次数及sink调用不是屏幕实际呈现帧数；颜色/光学仍未验收。此次V4L2 trace为空，不用它推导“没有成像”。

本机GTK为4.24.1，支持线性DMA-BUF的CPU `mmap → memory_convert`下载。因此采用：

```text
GSK_RENDERER=cairo
GDK_DISABLE=gl,vulkan,offload
```

当轮保留DMA-BUF和原PipeWire bufferpool，未启用`use-bufferpool=false`。匹配[GTK 4.24.1实现](https://github.com/GNOME/gtk/blob/2ea935e3ec680fb122f245b28e18c3495df8c344/gdk/gdkdmabuf.c#L147)及[官方开关](https://docs.gtk.org/gtk4/running.html#gdk-disable)。该CPU回退仅配置Snapshot，Phoc等其它进程继续使用原环境；后续可按任务测试其它路径。

已安装同ID的用户desktop和D-Bus service覆盖，图标显示“相机（Snapshot）”，原签名包文件不变。desktop采用直接Exec；服务目录为本轮新建，初次直接D-Bus激活仍使用旧缓存。读取真实Phosh session bus并`ReloadConfig`后，[原生激活](snapshot-dbus-activation-validation.json)确认新进程继承相同CPU环境；自己的无窗口idle服务已停止。没有修改Phosh全局GPU或默认应用schema。[配置事务](snapshot-launcher-install-validation.json)。

`was not recycled`是PipeWire交付与GStreamer持有账本不一致，不能当作普通慢帧忽略，也未证明内存越界；gtk4sink的pending队列警告则来自有界帧合并。Snapshot没有现成FPS设置，PW1.6.8相机配置没有处理FrameDurationLimits，降低候选caps不保证降传感器帧率。预览性能、缓冲所有权、拍照保存、切换、颜色及长稳继续开放。

## 其它本轮工作与清理

手机竖放后的IMX319同request RAW/RGB24组均非零。稳定6帧中，2ms RAW均值64.290/std0.756/max85；32ms均值69.864/std10.211/max387，92.35%仍≤80，RGB均值41.97/max153。曝光响应与非零数据已取得，不能据此认定正常光学成像。[直方图重算](upright-analysis.json)。首次guard因闲置WirePlumber持FD拦截、0帧，确认精确身份和PM闲置后才允许r2独占acquire；未停止策略进程。

S5K3M5的[候选源码](s5k3m5.c)保留917条OEM初始化和模式3的53条寄存器、WRITE8流控/30ms停流延迟，并修正PM引用、残留rail回收和selection高度。它**尚未编译或部署**；19.2MHz、本机P L2/L6电源和共享lease仍待实现/验收，link723.2MHz只是未实测候选。当时IMX319 lab有消费者；卸载父MFD的技术前提是先停流、释放并移除消费者。前摄纯色测试按用户延期；当轮没有新增照明、保存或转移场景像素。

[最终健康](final-health-validation.json)验证789项默认模块及加载note、49个相机载荷、958包及原944记录；两sensor/CCI/CAMSS suspended、四camera rails OFF/users0、MCLK1/2关，三DSP/SensorProxy/Wi-Fi/chrony保持。停止故障Snapshot后新增fault为0、taint0；蓝牙只观察、GNSS保持idle/dataworker0，无新GNSS SET或搜星，无刷写/重启。

[266项原生证据](evidence-validation.json)已私有导出并逐成员校验，包含失败、GPU故障、两轮CPU预览、包及启动配置事务。GNSS正CNR/fix、其它后摄、无SIM条件下尚不能验收的蜂窝业务、蓝牙/传感器长稳以及完整kernel/rootfs仍未完成。
