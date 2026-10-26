# k363 蓝牙驱动收敛包 r3

本修订把已有PM r2与本轮serdev注销/flush、QCA IBS分配失败重试和close收尾修复合为同一`hci_uart`。仅此模块字节变化，`btbcm`、`btqca`复用原363归档；无Image、DTB、USB、充电、音频配置、地址或密钥载荷。

沿用既有`reference/package-hardening-20261023/build-apk.py`的candidate入口及签名密钥，版本为`samurai-bluetooth-k363-0.1.0-r3`。不修改旧r0/r1/r2包或构建器。该入口的历史目录名`pm-candidate/`及文档名`PM-CANDIDATE.md`保留；r3内对应内容以本说明和新候选锁为准，包含上述完整修复。原363重建源也保留用于来源比较，实际候选C与补丁位于同包的`pm-candidate/`。

候选只适用于固定原363的配置、符号表与完整vermagic，来源见[source-lock.json](source-lock.json)。原固定基线提交为`ba61a62293e0f6bc5838c06f2e85e033e3d702a8`，不能以工作树当前HEAD或同名release代替实际运行基线。

新包先做完整模块链接、导入/依赖/ABI核对，再在两个独立目录签包并验签，以既有`validate-pm-package.py`实际执行隔离root中的r0→r3升级及文件/模式核对。运行状态和机型为fixture，安装使用`--no-scripts`；不代表手机安装或蓝牙功能通过。相同源码的ASan/UBSan与定向回归复用[既有离线结果](offline-validation.json)。

包内pre-install/pre-upgrade仍是既有r0边界检查，要求蓝牙服务已停止、模块已卸载且旧三模块为原r0字节。APK3脚本失败可能已提交载荷/数据库，不能依赖钩子阻断事务。后续采用须按现场owner、canonical路径、模块索引/trigger及回退条件安排；旧r2专用事务工具不能直接当成r3安装入口。本轮不执行现场预检、服务切换、depmod、模块加载或安装。

私有APK、完整模块、构建日志和隔离root留在现有私有输出及WSL目录；公开树只保留源码、补丁、锁和脱敏结果。正式结果由本目录新的模块/包验证报告记录，旧报告继续属于其原版本。
