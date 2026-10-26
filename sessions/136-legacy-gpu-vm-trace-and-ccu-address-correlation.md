# 阶段136：legacy GPU VM追踪与CCU地址核对

2026-10-12。以稳定132软件构建#136，新增msm_gpu_vm_update和msm_gpu_vm_switch_enqueue，默认关闭；不改GPU命令、全局debug、缓存策略或分配对齐。Image、770个模块、DTB、initramfs和完整rootfs四件套验证，实际只替换logdump。

首boot有31次SLIM TX DMA prepare失败与WCD934x efuse WARN（taint512），Phosh/Phoc存在。单项GPU诊断显式保留该已知告警边界，不能作为清洁运行验收。UID10000固定800×600 build场景像素Success，但退出后两次CCU READ TRANSLATION；有界70.369秒窗口桌面PID、DPU2/DSI0/WARN1保持，GPU仍失败。

追踪无丢失：24次map、23次unmap、9次页表切换、12次flush/11次retired。legacy managed VM未受旧vm_log_shift接口覆盖，先前历史未记录，不能以空记录证明映射释放。

故障TTBR所属VM共44次操作，无一次覆盖故障地址。7个转储BO全部精确对应其自身成功映射，RB颜色/深度/标志基址在各自映射内；故障比最近颜色BO低32KiB。另一VM同数值IOVA仅为巧合，不证明跨VM状态、UAF或unmap。ftrace mono和dmesg时间尚未建立偏移，不直接比较两者先后。

Mesa26.2.4固定crashdec离线估计停在末尾IB的CCU resolve/cache flush及内核提交收尾；不是实际发起故障指令的证明。原厂固定提交9668fcdc的A640与当前核对均UBWC3/HBB15；PAGE_SIZE分配及XML标志基址约束不能支持凭猜测改64KiB对齐。GPU问题保持开放，所有原始转储、地址、进程和日志留E私人目录。

可复核：reference/kernel136/legacy-vm-trace-validation.json、legacy-fault-correlation.json、core-bo-vm-validation.json、resolve-bo-offset-validation.json、decoded-stop-validation.json、ubwc-source-contract-validation.json。两次诊断和部署已执行且终态，不重放。
