# 156：首帧背光策略实机执行，首次 DSI 欠载仍待修复

已实际部署 #156；boot132/modules132/software132 与 Mesa149 修复保持。Phosh 从此前 uptime 79.67 秒提前至 20.62 秒启动，进程启动时间来自 `/proc/PID/stat`，不依赖校时后的文件时间。用户暂时外出，实体锁屏速度和画面验收待补。[启动顺序](boot-order-validation.json)、[时间证据](boot-timing-validation.json)

原厂 SOFEF03F 配置要求首帧后更新背光。新策略延迟正亮度写入与 panel follower 通知，DPU 在可睡眠提交上下文等待 TX complete 后放行，关闭屏幕时重置门控。它使用真实像素传输完成事件；CTL start/page-flip 不能代替该事件。实际 12 次亮屏均观察到 pending、PP TX done、成功等待与背光 ready 的顺序，ready 位于 TX done 后约 0.068–0.292 ms。24 次标准 DPMS 转换没有新增 DSI/DPU/GPU/WARN 错误。[补丁](first-frame-backlight.patch)、[实机时序](first-frame-order-validation.json)、[电源测试](cycles-validation.json)

首次启动仍出现 78 条限频 DSI 错误，因此全 boot 零欠载验收失败；首帧策略执行成功不等于永久白屏问题已修复。实际 logdump 读回、boot/persist、NV、原模块和 Mesa 库核验通过。93.09 秒启动记录无丢失，DPU/GPU/WARN 均为 0，taint0。临时启动记录器已停止并退出 boot runlevel，屏幕随后通过标准 PowerSaveMode 重新点亮。[启动](startup-validation.json)、[运行核验](runtime-validation.json)、[部署结论](deployment-validation.json)

20 项真实函数普通与 ASAN/UBSAN 测试通过，旧实现两个早亮负对照失败。完整内核、W=1、checkpatch 和 FAT 检查通过。新增 panel 状态放入既有 padding，实际 ARM64 类型的结构大小及原成员偏移保持。770 个模块中 768 个逐字节一致；两个模块仅 GNU build-ID note 不同，替换该 note 后全文件一致，原模块继续复用。[函数测试](actual-function-test-validation.json)、[结构兼容](panel-layout-validation.json)、[模块兼容](module-compatibility-validation.json)

155 正常启动与 156 异常启动的 13,302 个寄存器对照均确认读取前后 active=1。DSC 配置相同，PLL 差异位于校准/状态寄存器。异常 DSI worker 可同时复位控制器，CTRL 与状态寄存器差异不能当作静态配置原因。下一项 157 将检查首次接管时，固件 DSI 控制器在 PHY/PLL 重配之后才停止的顺序。[对照资格](matched-active-register-comparison.json)

完整原始记录仅在私人产物目录保存。[档案哈希](evidence-archives.json)。最初启动服务文件时间在 RTC/网络校时后产生负 uptime；此错误推算保留在私人原件，公开启动速度结论仅采用进程单调时钟。

原厂配置：[本地面板参数](../../linux-port/refs/19781/dsi-panel-samsung-sofef03f-m-amoled-dsc-fhd-plus-90fps-cmd.dtsi)。首帧更新属性与 TX complete 路径可核对 [原厂绑定](https://android.googlesource.com/kernel/msm/+/04749e7fec2a8a5784a984d09f03fd0f2715fd1b/Documentation/devicetree/bindings/drm/msm/mdss-dsi-panel.txt) 和 [SDE 实现](https://android.googlesource.com/kernel/msm/+/5ba475a485f6996c697d0547033374896738d0b6/drivers/gpu/drm/msm/sde/sde_connector.c)。
