# Session 75：A640 实际渲染与 SOFEF03F 花屏修正

最终 #76 已启用主线 A640/GMU，累计 39,096 次实际 Vulkan 三角形渲染、完整
4096 像素读回和 fence 校验通过。用户确认非连续时钟版本的纯白图没有噪点，
随后确认最终版本重新启动后的首次标准彩条清晰。两次最终启动完整日志无
DSI worker 错误、SMMU context fault 或 Oops，taint=0；混合显示回归共 12 次
关闭/开启通过。源码、失败候选与独立验收边界见 [kernel75](../reference/kernel75/README.md)。

## GPU 接入

SM8150/A640 的设备树、GMU 和 Adreno 驱动已有主线支持。本机此前的板级 DTS
显式禁用了 GPU/GMU；不是缺少整个 GPU 驱动。此次只启用两个 status，并指定
本机签名 ZAP 固件路径。实际 UEFI DTB 精确三处语义变化；继承的时钟、OPP、
GDSC、IOMMU 和 interconnect 配置不变。

从本机原厂固件安装 a630_sqe.fw、a640_gmu.bin 和完整 a640_zap.mbn 到真实
initramfs。七文件及 ELF/MDT 元数据和 LOAD 几何已校验；4 KiB 可重定位 LOAD
适配 8 KiB carveout。GMU v2.0.261 实际加载；GPU-SUDO 未启用。临时 Ubuntu
26.04 ARM64 Mesa 26.0.3 Turnip 测试包经 Ubuntu archive keyring 验证后只部署
到 /tmp，强制选择硬件 A640，逐帧核对红/绿三角形和蓝色背景、重复哈希及 fence。
这证明实际 GPU 任务运行，不以 renderD128 注册作为验收。

## 花屏与显示接管

用户照片显示整屏静止紫/青噪点，明确无闪烁。CPU framebuffer 截图文字正常，
纯白 KMS 图的 DPU CRC 正确，但用户仍见花屏。因此数字 scanout/CRC 不能证明
面板输出正确；GPU 渲染读回和物理显示分开验收。

原厂 PPS 与当前计算 payload 逐字相同。只读启动诊断证明继承的 DSC0/1 核心
寄存器也与原生设置相同。未改 DSC 几何、PPS、供电电压或 DSI 链路速率。
原厂没有 tx-eot-append 或 force-clock-lane-hs 属性，其解析默认均为 false。
关闭 EOT 的 #74 仍然花屏。#75 加入 CLOCK_NON_CONTINUOUS，并显式清除
controller/7nm PHY 遗留强制时钟请求，用户确认纯白正常。#75 的早期 DSI
错误直到首次显示电源循环才停止，故没有将它宣布为干净首次启动。

最终 #76 仅移除只读 DSC 诊断。首次启动 boot_id
`770389cb-a7fe-4b81-bddd-fec402a1c5b8`，在任何显示恢复电源循环之前提交彩条，
用户确认“彩条清晰，显示正常”；后续 9,036 次渲染和九次电源循环通过。
同镜像不刷写重启，boot_id `af922f36-bacd-481d-a5c5-21c8e3fada65`，另十二次
渲染和三次电源循环通过。两份完整日志均无 DSI/SMMU/Oops。第二次启动是
自动化证据，不虚构第二份用户光学报告。

首次 GPU 候选 #69 暴露旧帧冻结导致 drain timeout，以及旧 private object 二次
释放崩溃。修正初始化生命周期，使 finalization 只发生一次；旧命令帧无法自然
结束时停 TE/trigger，并要求成功复位的 CTL 输出掩码覆盖每个 stalled INTF，
才允许换 IOMMU 域。保留 session74 的双 CTL reset、清输出和取消空 kickoff。
对应增量为 0011；时钟/EOT 修正为 0012，均精确应用复现实际源码、checkpatch
零错误/警告。#71 只构建未刷入；各失败候选没有删除或冒充成功。

## 部署与边界

本轮 boot 写一次，logdump 写七次。最终 logdump
`607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0`；
boot `43ddcba2444e1672cd95205f6984c761eaeb59c83162cffdffb371c50a29c37b`。
设备端按 PARTNAME 核对后回读，与本地产物一致。配置、触摸、RPMh、EUD 和
真实 init/USB hook/SSH 身份保留；仅 boot/logdump，Android、数据、GPT 保留。
专有固件、完整镜像、CPIO、SSH 密钥及用户照片不入 Git。

#69 的 F1 回执后 device_shutdown 被失败探测阻塞，曾在确认只有 RAM 虚拟挂载
后用 sysrq b 恢复 fastboot。一次 #74 部署 USB 先断开未捕获 F1，初始部署脚本
拒绝写入；改以单次 OUT 完成和独立 serial/product/partition fastboot 检查后
才刷 logdump，记录 receipt_observed=false。最终 F1 均有回执和独立枚举。
早期 verbose console 尚未排完时两个 startup Ctrl-U 同步尝试失败，均未发送
原生命令；随后同一终端发送成功、数据帧无重试并关闭。EUD 内核传输未调整。

仍待验收冷断电、90Hz、休眠/恢复、亮度光学校准、全部 GPU OPP 压力、完整桌面。
全硬件目标保持 active；下一项本机电量计/MP2650，再推进无线、音频等硬件。
