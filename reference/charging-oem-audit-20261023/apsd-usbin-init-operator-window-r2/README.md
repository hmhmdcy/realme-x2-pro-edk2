# USBIN 操作窗口 R2：5分钟

本目录是临时helper的独立R2，**唯一生产行为变更**为 `usbin-init-core.h` 中 `UI_WAIT_MS 60000ULL` → `300000ULL`。`samurai-usbin-init.c` 与旧冻结版逐字一致，SHA `66042e413020467892de3ec60f536765206a9e6cf60c15b2fc362f0073c660fa`；core其余字节含换行逐字保留。旧目录、永久provider、主机端和DWC候选均未修改。

原500ms物理off稳定门、250ms写前fresh门、250ms轮询、一次masked bit7 clear、原值保存、readback/unknown、自持ref、显式commit及卸载条件全保留。没有新写/重试/预算/角色/其它PMIC操作。5分钟是本次人工操作窗口的保守工程选择，非原厂规定。它仍是绝对BOOTTIME截止：截止后不开始新写，不能硬中断已开始的regmap传输。显式restore_saved使用同一窗口常量，仍须本实例真实旧值和重新满足off门。

`protocol.json` 保留原schema/路径/action/fields，仅 `times.window_ms=300000`。state本身的schema仍为1，不能只靠schema识别版本，host须绑定新ko、core、protocol、boot/instance和独立新事务。不要修改旧001或把旧60s原件改写成新窗口实测。

`actual-state-fixtures.json` / `.jsonl` 是执行真实R2 `control_store/ui_work/state_show` 输出并解析的状态，不是手造报文。包含observed、armed（remaining300000）、61秒后waiting（remaining239000）、新鲜off后clear_verified/显式committed、精确300s零写timeout、blocked prewrite到截止且old_valid=true的零写timeout、251ms stale拒绝，以及同实例restore61秒后完成。硬件/OS是原fake边界，不代表实体结果。

`test-result.json` 仅新增5组截止影响范围测试，直接包含原12个模块函数和7个core函数；ASan/UBSan/Werror通过。原12组未重跑，引用原收据 `e97adf52392f6306890d287dacf050b25776cc13927717d13bfb97a559f6cb42`。新增边界为：61s仍等待并在500ms新off窗口写；300s前/整点/之后的绝对期限；截止前合格off可写、太晚不足500ms不能跨截止；阻塞prewrite跨300s零写/251ms stale依旧拒绝；显式restore同样继承5分钟。没有扩大大矩阵。

`build-result.json` 仅私有k363原helper ko、W=1无warning/error，intreeY、depends空、原vermagic。最终模块SHA和私有导出路径见 `delivery.json`；校验只认该冻结收据。没有Image或永久provider更新，没有设备、SSH、USB、PM、SDK、Git或共享源码/build/config修改。主机R2由另一代理独立复制，根会话负责审阅和现场窗口；本目录没有部署或自动控制入口。
