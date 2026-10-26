# 480：目标端验签及依赖模拟结果

主线已在真实目标完成一次执行，设备已归还。本次审计只读回收缓存，不访问手机/SDK。

实际 aarch64 apk3.0.8：475原字节的7 APK＋签名索引 `verify` exit0；精确7 pins 的 `add --simulate --no-network` exit0，stdout仅列出5项libcamera r32→r33、config/stack r27→r28。使用目标原信任集，无keys覆盖、allow-untrusted或force绕过；私有仓库/cache，scripts/hooks及全局log关闭。

前后72项APK全局清单原始JSON逐字节一致，含安装db、world、repositories、两处keys及apk.log。worker24107/start1639532终态passed，外部observe证明该进程不live；原始19文件归档6700B，SHA256 `b21369df38feba39d9a992dea67bd536d4cb67217f137efb98bf6919d0c1eea7`。外部健康两样本、约1.081秒，同boot/taint0/零新增所查故障，限制及服务保持。

仅证明原信任集验签和真实已装providers上的依赖模拟。未发生包事务，不证明实际安装、升级/回退或默认相机路径捕获。准备期收据仍是当时未绑定、未执行的快照；实际审计及原件hash见 [runtime-validation.json](runtime-validation.json)，复核入口为 [inspect-runtime.py](inspect-runtime.py)，避免与Python标准库 `inspect` 同名。
