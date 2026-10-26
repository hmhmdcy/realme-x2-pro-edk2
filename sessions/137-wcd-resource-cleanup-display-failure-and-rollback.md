# 阶段137：WCD资源清理、显示失败与132回退

2026-10-12。在已封存136源diff/镜像后复用C卷构建树，补入[上游WCD934x清理](https://lkml.rescloud.iu.edu/hypermail/linux/kernel/2603.1/03387.html)，并仅在首次NGD/BAM DMA失败时打印通道/分配状态。未改DMA分配策略、GPU命令或充电配置。W=1修改对象及完整构建无告警，checkpatch代码规则0/0，770模块及DTB与132逐字节相同，四件套完整hash/FAT精确回读通过。

实际#137/software132只刷logdump。首boot无TX prepare/WCD WARN/ENOSPC、taint0；这只是本次观测，不证明先前DMA/efuse根因。大量dsi_err_worker status=c（FIFO/MDP下溢）及status=0，3次DPU timeout；不可因无WARN而验收。初始PID快照过早为空，稍后Phosh/Phoc自主启动。BlueZ首次status未ready导致采集中断，仅补采剩余项目，分区操作未重放。被动EUD读发生EIO，失败记录保留，无重复com-up。

保存显示/clock现场后按当前boot守卫排空音频、无线、显示及追踪，freeze/F1各一次，只刷logdump回退132。新boot全量回读boot/logdump/live DT/GPT18/persist/770模块/11来源通过，taint0。28.692秒8次被动观察桌面PID保持且计数不变，DPU3/DSI0/GPU0/WARN0/TX DMA0；没有桌面重启、panel rebind、greetd标记或新GPU负载。首次回退快照PID也过早为空，以rollback-health-validation为当前桌面依据。

当前匹配rootfs132四件套已fresh hash；userdata未全量刷入。上游cleanup保留在源码/候选，137没有成为稳定镜像。下一项可修NGD未提交DMA错误留下TX槽位/TID的回收；不能擅自用GFP_ATOMIC、重试或删除WARN掩盖首错。

证据：reference/kernel137/audio-source-validation.json、audio-build-package-validation.json、first-runtime-validation.json、boot-error-validation.json、rollback-runtime-validation.json、rollback-health-validation.json、stable-build-package-validation.json。私有当前boot身份为E:/edk2-samurai-out/kernel137/embedded-boot-id-private.txt；rejected-boot-id是137旧boot，不是当前。
