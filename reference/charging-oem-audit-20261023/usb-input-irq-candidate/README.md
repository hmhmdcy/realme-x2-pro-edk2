# USB input：真实 PMIC IRQ 触发已有安全读取

本叶在实际 R7 FLOAT provider 上增加两个 threaded IRQ，IRQ 只把已有 work 重排为0；ONLINE、源类别和预算仍由原七字段两次稳定读取、原 decoder 与原 native 额度计算得出。1秒 fallback 未改，不发 APSD/PD/role/充电寄存器命令，不根据中断直接授权供电或 Charging。

候选未接入当前 DT、未部署，未测真实中断或图标时延。本轮只编一个私有对象，没有链接 ko/Image/firmware，没有访问手机、SSH、USB、SDK 或 Git。

## 精确变化和来源

基线 C `b712764f…7098`、FLOAT decoder `a17caa2c…548fd` 与 R7 实装收据匹配。`samurai-usb-input.c` 新 SHA `0fdafb8b3924e431efd67a888cbb88b8f5fe6de22dc400b009bf64cba34b7be5`；补丁 `usb-events.patch` 为 `778c68ec…d5f16`。12个原函数逐字保留，包括七字段读取、get_budget/native额度、get/set_property、poll、stop、suspend/resume和 native保留；准确函数哈希见 `review-result.json`。

新 `samurai_usb_event` 在同一个 input mutex 下检查 paused，只在未暂停时 `mod_delayed_work(...,0)`，不读取 PMIC、不通知一个伪造状态。`samurai_usb_request_events` 先取得完整命名 pair、传播 EPROBE_DEFER、拒绝部分/零/重复资源，再用 IRQF_ONESHOT 请求两个线程。两者都缺资源时保留 legacy fallback；Linux platform optional lookup本身可能把非defer的发现错误折成ENXIO，因此这里的fallback不能当“实际IRQ已经接通”的验收证据。

原厂同机19781 `pm8150b.dtsi:524/526,533/535` 将 usbin-plugin映射到 `<2 0x13 4 BOTH>`，usbin-src-change映射到 `<2 0x13 6 RISING>`。`board-irq.fragment.dts` 仅给出相同资源，IRQ号由真实 domain映射，不硬编码Linux IRQ整数。实际当前嵌入 EUD-off native DTB为 `9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358`；本叶直接解析其保留字节，未使用 FAT365的另一个DTB。

当前 `/soc@0/spmi@c440000` 是 qcom,spmi-pmic-arb、interrupt-controller、4 interrupt cells，PMIC2为qcom,pm8150b、reg2/0，Type-C节点disabled。固定实际源码 `drivers/of/irq.c:61–80` 的 parent walk先查当前节点显式interrupt-parent，否则逐级向父走，至有#interrupt-cells处停止。新子节点→PMIC2→SPMI即找到4-cell controller，根节点GIC的interrupt-parent不会提前替代这一走法。`of_irq_get_byname:583–594` 按命名索引解析，`:528–544` 在domain尚无时返回EPROBE_DEFER；`drivers/spmi/spmi-pmic-arb.c:973–1011` 验证四元组并取第4项触发类型。资源所有权/实际中断递送仍须后续真实probe证明，DT中的disabled Type-C没有被当成PD许可。

## 生命周期与正常 shutdown 窄修

probe初始化mutex/work后先paused=true，请求IRQ，之后才注册power_supply，再注册旧stop devres action，最后持lock解除paused并启动初次work。因此请求期间的IRQ不可能排到未发表的psy；第二次request失败时，第一个IRQ仍被devres回收，input在此之前保持paused。

逆序释放为 stop/cancel→power_supply unregister→IRQ释放→input释放。stop在lock内置paused并清udc_valid，解锁后同步cancel/join；IRQ线程在stop后只看到paused，不会在psy释放后重新排work，也不使用psy或regmap。PM suspend复用旧stop，resume复用旧立刻重排；没有加唤醒中断策略。

独审补上 `.shutdown = samurai_usb_shutdown`，wrapper只调用原stop。真实 `drivers/base/platform.c:1527–1537` 会派发该回调；`drivers/base/core.c:4875–4934` 的正常shutdown遍历不等于devres unwind，不能指望remove action在正常reboot时关闭新增IRQ/work来源。wrapper使正常shutdown也先paused并锁外join，再让PMIC父生命周期继续；它没有禁用IRQ深度操作，也没有引入新恢复策略。

有可用的单一精确DT节点时，register_board路径不再额外创建同名软件设备。具体板级probe仍验证realme,samurai、PMIC2/qcom,pm8150b、reg0x1300与父regmap；这不是跨任意多个compatible节点的provider发现框架。后续应只接一个板级实例，不能同时再创建第二个同名supply。

## 验证范围

`test-result.json`：16个受影响案例，直接抽取当前生产候选的event/request/原stop/newshutdown函数，Linux平台IRQ/工作队列边界fake，ASan/UBSan/Werror通过。覆盖无资源legacy、完整pair、部分/重复/零/错误、两处EPROBE_DEFER、两次request失败，paused时的即时IRQ、unpaused仅queue0、stop/shutdown之后late IRQ零queue。原stop还配真实pthread worker，cancel边界先验证mutex已释放，再唤醒需取得同mutex的worker并join；没有用复制的停机算法替代原函数。这不等于完整probe、真实devres unwind或所有硬件并发路径已执行。旧FLOAT预算测试没有重跑。

`build-result.json`：显式Ubuntu/root、原284 helper哈希/32GiB backing守卫，通过后只复用已验证source-float的W1 saved command，加-Werror、将source/output/dependency定向私有目录；单个AArch64对象编译rc0、无诊断，object SHA `a17ffaa09e08f7679fe1d658a2d54ef0aaffd74804350b112fb554c11c7dc88e`。旧source/config/cmd/object及所读shared源码前后SHA相同；无make、module或Image链接。一次编译前源码路径核对把SPMI文件放错目录而失败，未启动compiler；`build-pre-source-path-result.json`和原builder保留该历史，改成实际drivers/spmi路径后才执行这一次compiler。

测试生成ELF已从公开叶移入本轮现有私有object目录tests/，SHA `67e38583…cdfe4`、104328字节；原16例收据未改。`test-artifact-relocation.json` 绑定原runner和仅输出路径变更后的runner，未为路径调整重跑16例。公开叶不保留该生成二进制。

固定源码静态顺序与实际函数fixture、单对象接口编译是不同证据。未声称目前已收到PMIC IRQ、完成DT集成、升级USB预算、解决PM恢复或验收图标时延。当前候选供根与独立审阅者复核后另行决定接入。
