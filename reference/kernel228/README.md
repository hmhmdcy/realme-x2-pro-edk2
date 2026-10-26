# 228：FastRPC手机实测通过，树内产物待新启动验收

后续[230真正树内加载与五SSC再验已通过](../kernel230/README.md)，当前taint0；本页保留本阶段当时状态。

2026-10-16。已对227候选做一次受控启动验证：没有刷写，boot219镜像、Image183/logdump183、DTB、相机e49/fae1及r13/r8保持。**启动身份已经更新为228**，旧219/226/227 guard均不可再用于切换操作。

手机实测确认模块保活：守护进程运行时refcount=1，额外打开ADSP文件后为2，关闭后回到1；原189驱动是有1个FD但refcount=0。五类SSC流均收到测量并干净停止：加速度55、陀螺仪46、磁力计9、光线9、接近1。实际活动Wayland会话UID10000的三类Claim/Release通过，未改Polkit策略。[手机证据](native-sensors-validation.json)

自动服务也取得真实加速度/光线读数，三DSP及SensorProxy三项Has正常。第一轮启动观察器在taint核验处失败：仅FastRPC被外部M=构建标为O，taint=4096，五类fault计数全部0。原观察器失败原样保留，不改为成功。首个仅切UID的测试子进程被策略拒绝；改为核验当前活动本地会话、仅把一次性子进程放入其cgroup后测试，保留此前已通过的五路流日志，没有重复取流。

已把相同源码真正整合进canonical内核并通过树内`drivers/misc/fastrpc.ko`目标构建，W=1/modpost/同ABI和导入符号检查通过，intree=Y；没有在源码伪造intree宏。与已测外建对象的19540字节`.text`逐字一致。保留完整16798符号及772模块顺序，其余相关输入、Image/DTB/配置不变。[树内构建](intree-build-validation.json)、[代码一致](intree-code-equivalence-validation.json)

当前状态必须分开：运行中仍是外建`7ca5d442…`/50216B、O/4096；根文件系统默认文件已暂存真正树内`2abde0ea…`/50192B。**还需要受控新启动，才能验收树内模块加载和taint=0。** 没有对活跃驱动热换。原189模块`88553112…`在设备`k228-baseline`及私人输出备份，外建产物和中间源码也保留。全源码、增量补丁及分开的运行/暂存锁在[SSC内核目录](../../linux-port/ssc/kernel/README.md)。

重启记录：第一次命令生成器引用了错误目录，冻结已完成但Python明确报脚本不存在，内核重启未执行；核验同boot、FROZEN、restart阶段文件不存在及EUD仍绑定后，仅继续已有操作。实际执行后USB在末尾回执前断开，随后重新核验唯一设备及product，再发一次fastboot reboot；新Linux身份与分区读回确认。没有重复未知状态下的切换或刷写。

[最终健康](final-health-validation.json)：三DSP、Wi-Fi和chrony正常，GPS0/Signalsfalse/刷新30、watch空闲且data worker0，BT关/无连接，相机与CCI/CAMSS休眠、前摄双轨关/用户0。模块786文件除目标外785不变，944包数据库与程序/配置不变，NV/persist和boot/logdump读回保持。当前4096仅为外建FastRPC标记，无WARN/Oops/GPU/DSP/BT重组故障。

[119成员私人原生归档](evidence-validation.json)核对逐成员完整性，包含初次观察失败、策略拒绝、修正后Claim、两种模块及暂存事务；最终健康另以原生`k228-final-health`和宿主收据保留。归档指纹和身份数据未公开。

用户随后说明天亮，主流程优先做[229白天颜色测试](../kernel229/README.md)，干净树内启动仍待办。226的168h XTRA是前一启动的证据，本启动没有手工搜星/注入，也未重测该有效期。GNSS零CNR、后摄、SSR/DMA排空、reclaim−22、传感器物理精度/运动及全机长稳都未验收，完整goal继续active。
