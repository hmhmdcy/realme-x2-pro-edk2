# USB供电软件通知的系统PM修正候选

2026-10-24。依据[实机03调用栈](../../charging-session-20261023/pm504-wakeup-evidence/README.md)修正当前d046。新模块尚未装入，手机仍为d046；充电/温度参数、桌面、Image和相机保持。

在driver.prepare置pm_prepared，setter和poll使用同一mutex决定立即通知或标记pending；driver.complete清门并只发布一次pending。power_supply_changed自身仅取spinlock/持有唤醒源/排work，不同步回调属性，故与prepare共享mutex，避免“解锁后准备已开始才发布”的窗口。当前内核prepare先于所有suspend，complete在恢复或中止收尾执行。旧suspend/stop/resume原样保留；不在complete重新清掉已恢复的UDC额度。

真实两路IRQ在准备期间通过原power_supply设备单独上报pm_wakeup_event；正常IRQ排原稳定双读/解码工作不变，预算不从IRQ推断。没有禁用wakeup_source、屏蔽IRQ或改全局PM计数。物理插拔唤醒仍需实机验收，模型不能代替它。

16个原函数及a17 decoder逐字保持；仅setter/poll/event调用点和PM ops表变化，新增三个小函数。八组实际C函数测试通过：原500mA上限/非法值、挂起预算撤销和poll合并、原暂停/恢复与新鲜额度保持、prepare-only及撤销后abort、真实IRQ独立唤醒/paused、未发布PSY、poll错误及一次complete。OS边界是模型；首次缺to_delayed_work的测试stub编译失败已保留，生产源码未为此放宽，补stub后重跑原先未执行的八组。

实际单模块构建复用原284存储护栏与旧builder方法，私有source-view，不重建Image。W=1/KCFLAGS=-Werror零诊断，KO84005fae…/94440B，48个强导入全来自实际502内建导出；已核当前504相对502的config/export兼容原件，旧d046与shared/R7/502输入保持。vermagic、in-tree Y、AArch64及GNU note核对；不是实际新模块驻留/完整类型ABI或PM验收。

实际[正向与逆向包](cohort-result.json)：只含USB84005与manifest2419；source为当前504/d046/34ead，逆向精确恢复d046/34ead。保留当前bootedd/logdump4453、charger97c/保护7848、500启动和481/468。两包成员root0600、固定元数据、逐成员读回和确定性检查通过。仅准备，未stage/加载；native provider不热卸，更新与回退都需冷启动。下一步将已有安全冷stage/正常重启工具绑定当前504和新采用guard；不使用旧502/18e8的运行身份，不写boot/logdump。

当前新boot的MAC缓存应按实际0/0或终态1/1绑定同实例，只读保留；不能套旧boot的已消费report SHA或为了满足旧门而重新采集。原MAC失败仍保留。实际冷stage仍须保留Full/保护/fault并进入INHIBIT，两文件替换只算runtime_pending，新boot真实note/guard与PM才决定采用。
