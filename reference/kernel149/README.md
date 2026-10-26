# 阶段149：A640 Vulkan CCU 修复与实机部署

2026-10-13。本阶段已修复并部署当前可复现的 A640 自动 VM_BIND CCU 翻译故障。手机仍为内核 #147，运行 software132 加 Mesa149 本地库补丁；没有刷写分区或重启。

原驱动的 Vulkan 像素测试若保留图像前方的小缓冲区，相关地址仍有映射，可能掩盖越界读取。本阶段在绘制前释放这些缓冲区，成功复现 CCU READ TRANSLATION 和 VK_ERROR_DEVICE_LOST。同构建基线和系统原库均在第一次绘制失败，完整 core 已立即保存。所有 VM_BIND 调用成功，故障地址位于图像映射前方 8192 字节、等于其起点向下取整到 64 KiB 的地址；该地址的页表末级项为零。命令解码中的颜色元数据和 resolve 地址与图像映射对应。原驱动用 sysmem 绘制同一空洞用例通过。

修复只把 A640 自动 VM_BIND IOVA 起点对齐到 64 KiB，覆盖普通低地址分配和自动 capture 分配。显式 capture/replay 地址、映射长度、稀疏偏移、旧式路径和其他 GPU 保持原语义。公开补丁见 [0015](../../linux-port/patches/0015-mesa-turnip-a640-vm-bind-iova-alignment.patch)。补丁在 Mesa 26.2.4 原文件上实际应用后，其源码摘要与已编译候选一致，见 [patch-verification.json](patch-verification.json)。

[regression-validation.json](regression-validation.json)保留全部 13 条测试收据：10 条进程返回成功，3 条失败。两条是原驱动预期复现失败，一条是首次并发测试遗漏 Wayland 环境变量造成的工具失败；修正后并发测试通过。没有把失败删除或算作成功。

修复库在候选和系统部署阶段共完成 185 次像素读回、160,820,781 个像素，零差异。覆盖未映射空洞、1x/4x MSAA、RGBA8/BGRA8 sRGB/RGBA16F，以及手机尺寸和小尺寸。部署后的空洞测试经过 25 次 GPU 挂起和恢复，追踪无丢失；Vulkan 与 GTK OpenGL 并发的两个进程均正常退出。16 次稀疏重绑定和两次旧非对齐地址重放，数据均一致。GNOME Settings 在强制 GMEM 和默认策略下各完成 18 次面板切换，经 quit action 正常退出，各观察 60 秒无新增故障。

最终累计 GPU fault 为 3：进入阶段前的 1 次，加本阶段原驱动对照产生的 2 次。部署后新增为 0；内核 taint 为 0，WARN/DPU/DSI/DMA prepare 均为 0，原启动和物理桌面 PID 保持。包数据库和 greetd 配置摘要保持。见 [final-verification.json](final-verification.json)和 [fault-analysis.json](fault-analysis.json)。

部署采用同目录暂存、fsync 和原子替换。系统库 SHA256 为 `97f3638851b534070f649fabfbdbb3d330b4ad0e2b0ea93b78026ad71d78fb5e`。手机持久备份 `/var/lib/samurai/k149-deployment/libvulkan_freedreno.so.original` 的 SHA256 为 `c72f5ee34e9f4fcf200e4987285f6fdfef4442fd146b77a4c0d1cbf5d5525955`；同目录保存已部署库、源码补丁、部署收据及 [rollback-turnip.py](rollback-turnip.py)。回退脚本核对当前库和原库摘要后恢复原文件，本轮没有执行回退。

这是 `mesa-vulkan-freedreno-26.2.4-r1` 的本地库补丁，包数据库版本没有伪造。普通 Mesa 包更新可能覆盖该文件，届时须把公开补丁加入对应源码构建；旧完整 rootfs132 镜像也不包含本次库更新。当前手机文件已持久写入，主机修复库位于私有 `E:/edk2-samurai-out/kernel149/libvulkan_freedreno.so.fixed`。可复现构建源码和配置仍保存在手机 `/var/lib/samurai/k148-mesa`，SDK 位于 `/tmp/k148-sdk`。

工具限制同样保留：首次候选像素汇总 printf 参数顺序错误，但逐次像素结果正确，已修正工具；一个早期桌面计数把同时运行的临时无头 Phoc 算入，后续按 UID10000 复核了物理桌面。无头 Settings 缺少 Mutter DisplayConfig 服务，因此只验收面板生命周期，不代表完整显示设置功能。进入本阶段前的 GNOME 故障完整 core 已到期，不能声称恢复了该 core；本轮依据新复现的同类 CCU 故障完成修复。较大 GTK 命令解码的超时及范围限制另行记录。整机显示启动、音频、充电和其它适配问题仍保持既有边界。

GTK第4帧已完整解码，含55个bin render标记和4个resolve标记，见 [settings-command-validation.json](settings-command-validation.json)。首次请求解码12帧超过90秒；随后前三帧完整解码未出现GMEM，工具中“前三帧必须含GMEM”的断言失败也保留。最终只选择第4帧解码，不能把它扩展为全部帧的统计。

14份原始归档（13个测试加部署备份）全部保存到手机持久私有目录，并下载至主机逐一核对SHA256。11份临时源码已存档后移除，重复临时归档释放38,586,637字节；构建、SDK及原始证据保持。测试进程、临时追踪和待取core均0；诊断卷已关闭，镜像保留。见 [archive-index.json](archive-index.json)、[host-archive-verification.json](host-archive-verification.json)和 [closeout.json](closeout.json)。原始地址、启动身份、命令和进程日志只存私有目录；恢复测试前应重新核对实际设备状态。
