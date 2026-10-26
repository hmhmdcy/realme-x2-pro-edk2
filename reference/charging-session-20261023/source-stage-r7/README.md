# R7 两文件磁盘 stage 候选

本目录纯离线实现/测试；没有执行SSH、手机、SDK、服务或重启动作，没有修改 main、冻结r6/v2、thermal候选或共享源。它只为根会话后续明确协调的120秒窗口提供一次性事务，不自动借用相机/蓝牙窗口。

执行入口是 `python3 -B stage-r7.py --execute-r7-stage`，从stdin读取 [严格8字段request schema](request.schema.json)。guard固定为原`/var/lib/samurai/k449-adopted/boot-id-private.txt`。预期boot UUID、SoC `/sys/devices/soc0/serial_number`原始字节SHA256及compatible SHA256必须由根会话采用后传入；没有DT serial或其它身份fallback。

需要现成mode600、root保护的 `/run/samurai-charging-source-stage-r7-window.json`。其字段为 `transaction,owner='charging',token,boot_id,camera_released=true,bluetooth_released=true,exclusive=true,issued_boottime_s,expires_boottime_s`，与request匹配且 `issued<=now<expires`、总租期不超过120秒。根协调器负责创建/清理自己持有的租约；worker不猜测窗口或清共享lease。关键步骤复读boot/guard/SoC/租约，原service flock以非阻塞独占方式持有到结果落盘结束。事务目录固定在`/root/charging-management-20261023/<transaction>`，必须全新；失败/成功旧目录均不可重放。

实际顺序：

1. 核payload长23617、SHA `4222242f…3685978`，只接受两个准确member、root owner、mode600、mtime0和各自完整hash。旧manifest必须`944f…4202d`，新必须`5638db4c…9552c68`。JSON差异只能是USB module/installed-file hash及adapter_revision=r7。charger fac827…、manager61451…、protection75b97…及所有其它manifest条目不变。
2. fresh加载**实际安装的614 manager**，调用其`verify()`并对三件resident模块调用`loaded_matches()`。核精确本次FLOAT PMIC七字段、old native100mA、source ENODATA/Unknown、source+ACOK在线、REG08双INHIBIT，以及无cached fault/stop/latch/timeout等的准确r6占位样本。它不是健康充电样本：valid=0、age=-1、flags/fault=0均明确只是源早退占位。
3. 独立重新读取保护health/present及原provider的protection_state（getter每次实时MAC校验，没有cached Good fallback），并读取原gauge标准温度/pack/FLAGS，拒绝TCA/OCA、无效保护或越界。整组观测跨度≤3秒、返回后≤1秒。PMIC读取逐字复用已有query-fixed-telemetry：`/sys/kernel/debug/regmap/0-02`、name=`pmic-spmi`、range=`0-ffff\n`，`pread(fd,9,reg*9)`，只读。没有消费MP2650 REG14；cached fault=0不被宣称为新鲜REG14无故障。
4. 备份两件旧内容及600mode并fsync。持有原flock时直调fresh manager的`command(old,'stop')`，同步读REG08验证`&0x18==8`；不调用rc-service重入锁。即使后续REG08看似INHIBIT，stop抛错仍失败、绝不替换。停后重新取独立fresh FLOAT/保护证据。
5. 先USB ko、后manifest：同目录独占临时文件→完整写→chmod600→文件fsync→atomic rename→父目录fsync→新bytes/mode读回。只写这两个准确目标。再用不变的614 manager `verify()`新磁盘manifest，USB的`loaded_matches()`特意以旧ko备份比对resident note，charger/protect仍比原磁盘文件；现场三notes、相机/四服务、OpenRC marker保持。

不调用模块加载/卸载、reboot、AUTO、PMIC写、保护配置写或新charger策略。DWC3仍持有旧c77724… provider，stage后结果必须记录`resident_usb_sha256=c77724…`及note摘要，`source_float_runtime_fixed=false`，`runtime_pending=true`。新7d4e0f… USB ko只在根会话协调一次**原Image正常重启**后生效；本事务不承担该重启。

普通写/rename/目录fsync错误先读回实际目标。只有旧/新准确hash和600mode都可证明时才回退两件旧文件，仍保留INHIBIT，不运行AUTO。目标读不到、出现第三种内容或mode异常时是`UnknownWriteState`，不盲回退。回退失败也不会重试或启动其它修复。租约/身份变化或过期后不继续磁盘恢复；结果保留partial-files，必须人工审查，不能据此重启。

给根重启守卫的stage结果要求：`schema='samurai-source-stage-r7-result-v1'`、`phase='staged'`、`staged=true`、`runtime_pending=true`、`terminal=true`、`stop_verified=true`、`disk_state='r7_files_staged'`；primary/stop/recovery错误均null、unknown_write_state=false，且没有receipt_error/close_error。两件`final_files`必须是准确新hash/mode600，resident旧USB仍c77724…；还需host确认worker PID终态。**不能只凭磁盘新manifest或staged单字段认定runtime修复/允许重启。**失败和未知状态的原始结果、备份、before/stopped/after观察、events均留在独占事务目录；结果不能冒充新boot guard。

[test-result.json](test-result.json)提供 `passed` 和绑定实际文件的 `worker_sha256`。仅12项定向测试，执行真实stage顺序及真实临时文件写/fsync/rename边界，覆盖USB/manifest分别写失败、rename已完成后报错、目录fsync失败、回退失败、stop失败、未知目标不回退、精确payload/delta、fresh保护拒绝、实际lease/SoC gate和重复目录拒绝。设备/manager边界为fake；没有重复已有67/51/62套件，也不构成实机验收。
