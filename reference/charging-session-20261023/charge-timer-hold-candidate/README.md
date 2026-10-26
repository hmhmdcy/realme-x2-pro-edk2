# 已确认停充期间的累计计时：离线候选

此版已由[记录实际stop读回时间的R2](../charge-timer-hold-r2-candidate/README.md)替代。04ff91仅为未安装的离线中间产物，原件保留；后续使用R2。

2026-10-24。当前手机仍使用 charger97c；本候选没有安装、重载或访问手机。用户暂不方便现场测试，先完成离线修正与单模块构建。

旧实际 `sm_step_locked()` 在 TCA/温控/明确 INHIBIT 已成功执行 `sm_stop()` 后，仍按接线的 BOOTTIME 差累计周期。离线执行旧实际函数已复现：35991秒时因TCA成功停充，再等待12小时，计时仍变成36000秒并永久锁存。时间来自模型，不是让手机实充12小时，也不证明本机自然出现过此事件。

固定原厂 Android R `23172a1571bd91156032cc9fef16284a82b63d2c` 的 `oplus_charger.c`：`oplus_chg_other_thing:6933–6945`按存在供电累计；但 `oplus_chg_voter_charging_stop:4151–4163`在异常输入、温度/电压停止时将计时归零。原件缓存SHA为 `6cfb97b4367afe25094f3f342db4c9cce7982a22708371bc08ac6ed8bc9aa2d4`。本候选不照搬反复归零，保留已经累计的时间，只排除确认没有充电的等待段；未知2719 TCA仍只解释为停止请求。

只改实际97c的私有状态和 `sm_step_locked()`，增加 `charge-cycle-hold.h`；所有原有策略、MAC、Full、温区、CC/CV、stop/apply寄存器操作和5秒计数保持。只有本驱动上一轮实际成功停充、未锁存故障且本轮完整样本/已知在线/保护有效时，才排除上一段停止时间。shadow、停充失败、未知/坏样本仍保守累计；真正超时和坏时钟不会被暂停、AUTO或Full清除。真实断源和合格Full继续使用原边界。没有增加状态变更或查询来验证TCA正常原因，也没有提高限流/电压。

[定向测试](test-result.json)执行旧/新实际 `sm_step_locked()`，保留实际policy/core/full/cycle，仅采集、寄存器和时间为模型。旧逻辑6断言复现；新逻辑8组68断言通过ASan/UBSan/Werror，覆盖TCA恢复后继续累计并在10小时停充、INHIBIT、温控、未知源、停充失败、shadow、坏时钟/真实断源和亚秒余量/溢出。第一份fixture未使用变量被Werror拒绝；第二份fixture把生产的ETIME写成ETIMEDOUT，修正后03通过，生产候选未因此变化，原01/02输出保留。

实际编译沿[既有单charger构建器](../charger-reattach-observation-module-candidate/build-ko.py)和原284存储检查，仅替换经哈希验证的C及新header，复用现有Image配置、生成头和导出；构建器不安装模块。离线通过不等于实际长周期/温界/TCA验收。
