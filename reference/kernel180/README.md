# 180：PDR 世代与释放修复、父中断退出及剩余离线写错误

2026-10-14。基于179的实际函数锁阻塞重现，完成PDR锁、端点/状态世代和对象寿命修复，并在WCD清理children前同步停止parent IRQ。本轮实际构建、部署内核180；随后一次受控ADSP停启仍因离线IRQ写错误未通过。PDR超时、IRQ读洪流和ASoC错误在该例为0，原生左右声学复测通过。180已被181替代，历史失败保留。

## 修复与验证

[补丁](pdr-and-parent-irq.patch)使注册/locator事务等待退出list_lock，客户端回调也不持该锁；事务使用地址快照和服务器世代，indication序列防止旧查询覆盖新通知。DEL检查原peer，ACK发回原端点；真实/coalesced DOWN仍在新状态前清理资源。服务器更换、删除、lookup退役和release明确完成旧注册事务，不等待超时。失败lookup移到retired并保留到回调/worker停止后释放，避免锁外等待后的悬空指针；normal/error release均与locator回调配对。

[完整PDR源码测试](pdr-host-validation.json)使用本树协议header：27场景、六负对照，ASan/UBSan通过。[SLIM/MFD](host-tests-validation.json)91场景、九负对照，包括parent IRQ停止/同步/重建20周期。总118函数场景、15负对照；checkpatch和W=1改动对象无警告。完整编译、FAT回读与770模块兼容验证通过，只有两个模块的build-id不同；保留DTB/boot172、UCM173、15显示源163及其它音频配置。[构建](build-package-validation.json)

最初完整编译通过，但打包因暂存路径仍为modules-root176停止，未覆盖旧目录；修正为180后重新构建。首版Image/源码和日志保存在私人attempt1文件；源码替换器两次因匹配范围断言停止，未写生产文件，改为限定listener函数后执行。初期checkpatch缩进问题和fixture声明问题均在部署前修正，最终收据是已修正版。

## 部署与真实恢复结果

从旧176新取启动身份、完成停机/冻结。一次F1 OUT完成但无设备回执，手机仍同boot；确认解冻后进行EUD诊断。RX轮询活跃但接收/f1/queue为0；重绑串口将AHB2PHY配置从0设为0x11，仍无接收。`04040404`包含COM低字节信息，不能单凭该值证明MMIO损坏；具体接收异常原因未定。两个被动窗口均无数据；COM reset探测在WSL无9505时退出，没有发送setup/probe。

依据本树Linux uapi及eud_reboot_cmd，验证同boot/全停机/冻结，停止EUD串口、关闭其CSR_EUD_EN，再仅一次RESTART2("bootloader")。关闭EUD时USB先断开，提交JSON未捕获；以新观察的目标fastboot设备、产品和64MiB logdump几何确认切换，只刷logdump180。boot/persist/NV保持；不把主机OUT成功当作F1已接受。流程源码和私人日志保留。

[初启动164.39秒](runtime-validation.json)是新#180、taint0、单声卡/桌面、WCD0x411及MBHC/jack各一次，PDR/IRQ/ASoC/DMA等所列故障0，分区/NV核验通过。[ADSP一次实际offline→running](adsp-restart-validation.json)回收card/两map/一MCLK/五consumer，两旧句柄EIO，再自动恢复HiFi并成功录音；但窗口IRQ config72、mask6，测试失败，其余所列故障0。故障不能因资源恢复或后来出声改成通过。主机私人失败包`k180-adsp-failed-private.tar.gz`保存原始日志。

[原生四例](dmic0-ucm180-low24-analysis.json)检出左右，相关0.9726/0.9639、功放关闭参考差22.11/42.89dB，无削顶。原始capture的kernel_build仍误写176；执行脚本已检查#180，录音boot-id逐字等于已验证#180 runtime。修正仅作用于派生标签，算法和数值不变，原始包及旧分析保留，[更正依据](capture-metadata-correction.json)。不把错误标签隐去或改原始录音。

180最后停机仍产生同类离线清理错误，记录在181私人preflash/quiesce包；180不是干净SSR回退。其Image/logdump及176回退均保留。181只对已DOWN的main MAPLE缓存切换软件清理模式，再销毁缓存；具体修复和当前部署见[181](../kernel181/README.md)。完整goal仍active，耳机、音质/保护、自动crash和更长PM仍需验收。
