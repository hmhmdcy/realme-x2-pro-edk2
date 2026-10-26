# k363 蓝牙模块固化来源

第二轮已确认：APK3的pre-install/pre-upgrade失败不阻止载荷和数据库提交，这些脚本仅为advisory。必须在APK调用前使用外部前置校验；真实隔离事务与回退结果以[STAGED-ROLLBACK](STAGED-ROLLBACK.md)为准。旧签名包及其中的历史文档保持不变。

实际固化的是 `7.3.0-rc6-rmx1931-samurai-k363+` 的三个模块，来自已经部署并核验的 kernel363 模块归档。不是旧 k132 模块。模块字节、AArch64 ELF、依赖、vermagic 和 build-id 在打包前逐项核对；安装前脚本检测当前文件同字节，不切换服务或模块状态，不运行 depmod。其返回失败不能当作事务被阻断。

固定内核提交 `ba61a62293e0f6bc5838c06f2e85e033e3d702a8`。`current-source-validation.json` 来自该提交的 Git 对象，随包保留实际蓝牙源文件和板级 DTS。该提交 `hci_qca.c` 的 SHA-256 为 `645ded4980918a2d0a22dd2d56327bbc69c08e3689e9d313158f0d263e291d90`，与185修复后的源码完全一致。附带185补丁的基线是其本地 `8f50e48fc96bb72540b6efe8b2add269dc889c4b6ea750dc5ff7a370b5a4d30f` 源码；需要既有 phase 诊断上下文，不能在当前已包含修复的源码上再套一次。

185修复仅处理有限功率脉冲窗口的前导 NUL，以及短写和 flow control 的错误处理。旧 phase5 高速启动重组问题没有据此被证明修复；234诊断候选没有纳入本包。配对、连接、蓝牙音频及外部事件唤醒需要独立实机验收。

363原构建证据在仓库 `reference/kernel363/boot-candidate-build-validation.json`：778模块同release，depmod未解析符号为0，initramfs内三个蓝牙模块与实际模块树一致。重建应复用该提交、相同内核配置和构建环境，另开 Linux 文件系统构建目录；禁止在其它会话的共享构建目录执行 make。原配置SHA `23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed`，完整 Module.symvers SHA `0837fdc36f1bd6ab16109d4852883566b8fe42e5bb640771e30afb7822779223`。只构建 `drivers/bluetooth/{btbcm,btqca,hci_uart}.ko`；不要用局部 modpost 结果覆盖共享完整符号表。本轮复用既有可信二进制，不宣称重新编译已逐字复现。

204 RX wake/sleep 的板级改动已存在于当前363源码/后续启动链，随包 DTS 用于来源核对；包不包含任何旧 boot、Image、DTB、NV、配对密钥或校准资料。音频173的 helper/两UCM已在 `samurai-platform` 配方逐字固化，183的音频修复属于内核，不应误算成UCM包的功能。

本包不是新功能部署，只把已运行的三个文件纳入可验签包管理。当前文件所有权仍须在设备窗口核对；如有现有包拥有该路径，应确定准确的替代关系或重包该所有者，再模拟事务。不得以允许覆盖任意包的参数代替该核对。
