# 确认停充后暂停累计时间：R2已装机

2026-10-25。[R2已实际冷更新、正常重启并fresh采用](../../charging-management-20261023/charger-timer-activation-result.json)，当前chargerbef4/manifestf15ecc、bootbc612，USB13f41保持；[新组合RTC15.439秒](../../charging-management-20261023/charger-timer-rtc001-result.json)及原key/NCM自动恢复通过。无人值守自然放电/回充与计时暂停实测运行中，尚未得出通过结论。以下源码和离线结果属于安装前准备，实物十小时/TCA/温界仍未验。

问题与原厂依据见[前版说明](../charge-timer-hold-candidate/README.md)：旧实际driver在TCA等原因已成功停充后仍累积接线时间，模型中已复现误到10小时并锁存。原厂温控/电压停止会重置计时；本方案更保守，保留已累计值，只暂停能确认没有充电的时段。TCA仍是停止请求，不能因此判正常Full、清fault或授权充电。

私有 `timer_hold_confirmed` 仅在实际 `sm_stop()` 成功读回、已知在线、无锁存故障且属于INHIBIT/安全等待时建立。下一次还须有完整样本、有效保护/已知源；未知、坏采样、stop失败或shadow仍保守计时。既有超时、时钟回退、硬fault和真正断源/Full的规则保持，所有原策略、MAC、CC/CV、温控和寄存器动作不变。

R2还记录**首次成功停充读回之后的BOOTTIME**。停止写入若耗时2秒，这2秒仍累计；连续已停止的轮询不重置这个时间戳，也不重复收费。前版04ff91仅为离线中间产物，未安装；其完整源码/测试/构建结果保留，本版替代它。

[实际函数定向测试](test-result.json)：旧实际函数6断言复现；新实际 `sm_step_locked()`、policy/core/full/cycle共9组76断言通过ASan/UBSan/Werror。仅采集、寄存器和时间边界为模型。覆盖等待恢复后继续累计并保留真正10小时锁存、INHIBIT、温控、未知源、停止失败、shadow、坏时钟/真实断源、亚秒余量/溢出和2秒慢stop。不是实物10小时循环或TCA语义验收。

构建沿既有单charger构建器、原284存储检查和现有内核配置/导出，只替换当前97c的C并增加一个header；未重建Image或使用SDK。采用[当前冷更新入口](../charge-timer-cold-update/README.md)保留旧运行状态到正常重启；[两分支逆向入口](../charge-timer-cold-rollback/README.md)及恢复启动检查也已离线通过。不能套旧10ec→97c事务或在Full中热卸。物理USB唤醒、温界和完整电量循环仍待实测。

[实际单KO构建](ko-result.json)通过：模块 `bef4dba7…97d6f`、156784字节，54个强导入均对应既有内建导出，W1/Werror零诊断；原两个make子进程均终态0，跟踪输入前后不变。[两文件配套](cohort-result.json)：chargerbef4/manifestf15ecc，forward9d26ed、精确97c/5ef4逆向c72589；USB13f41、保护f6bef和服务83469保持。前向已绑定真实事务并安装，新组合另有独立启动和RTC结果；逆向未执行。
