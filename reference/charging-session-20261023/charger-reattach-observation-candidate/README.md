# 接回后有限短观察候选

当前IRQ001原件中的三次手动拔插，source online事件接收到Display明确Charging估算约2.10/2.10/2.08秒；严格完整周期因三短off均未满足离散采样门而未通过。脱敏事实与限制见[相对时间线](../../charging-ui-audit-20261023/icon-irq001-timing/README.md)。这些证据支持评估剩余观察等待，不能承诺消除APSD识别、BQ芯片每秒数据更新或屏幕绘制时间。本候选未部署。

基线为实际charger10ec对应的R8 C `ed2e1d4d…a144c`。完整[samurai-mp2650.c](samurai-mp2650.c)仅四处差异：include新header；私有charger结构增加零初始化观察状态；在既有`source=-1/0/1`计算后记观察；锁内poll用helper选择下一delay。[source-reuse.json](source-reuse.json)保存每处原文/新文与逆向逐字等于基线的证明。原完整安全step、硬件事务、通知内容和锁外通知、notifier、sysfs、INHIBIT、Full与暂停/恢复/移除函数均未改；无需复制九个未变头，构建者应按原thermal build收据复用它们。

[reattach-observation.h](reattach-observation.h)的状态仅由既有`c->lock`保护。初始online不触发；unknown不产生offline。已有source+ACOK一致online即使随后预算ENODATA，仍可作为观察提示，绝不替代完整采样最后重核或授权充电。真实off→on只开启一次3秒BOOTTIME窗口；窗口内反复off/on、unknown和重复notifier都不能续期，也不保存窗内off供过期后重用。过期后须新的窗外真实off才可再触发。250ms是完成当前work后的排队延迟，真实step/I2C/调度时间另计；最后不足250ms夹紧至剩余毫秒，过期回1000ms。时钟回退取消窗口和off证据，加法溢出拒绝arm。暂停不排新work，恢复/耗时work跨截止不补跑积压。没有新线程、锁、timer或work所有者。

[test-result.json](test-result.json)六组受影响检查使用真实header、从完整候选逐字抽取的poll/notifier/source表达式与原Full/timeout helper；OS、硬件step和通知边界为fake，不把它当全驱动测试。原exec `7ff7f3`终态0：普通WSL用户态GCC child232400与fixture239304均wait0，ASan/UBSan/Werror无诊断。覆盖首次on/unknown/真实edge、窗口内flap不延期、硬截止/夹紧/长间隔/异常时钟/溢出、实际source的预算错误语义、100次原notifier不碰状态、paused/慢work、原5秒计数及36000秒门不随4Hz调用加速。旧矩阵未跑。首exec `3189f6`仅fixture unsigned三目表达式被Werror拒绝，生产源码未变；原结果和两个测试源原字节保留在history。修正显式int cast后使用全新tests-02输出，没有重放tests-01。

完整健康step仍有两次保护属性各5MAC及一次0071；短窗是额外I2C负担，未缓存Good、删MAC等待或跳过保护。下一步仅由root审核并在独立叶构建实际Image502匹配的单ko；本叶没有模块/Image构建、设备/SSH/USB、SDK、storage guard或Git操作。实际收益、age/错误、净电流及目标DBus/屏幕表现仍需受控实机窗口。
