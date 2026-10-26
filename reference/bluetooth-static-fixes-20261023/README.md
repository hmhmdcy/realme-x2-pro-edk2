# 蓝牙六类静态问题修复与离线验证

2026-10-23。两项P1优先修复，六类静态问题均已修正并离线验证。进一步收敛为完整内核模块及r3签名候选包、RAM helper的平台配方增量、工具内的统一入口。没有连接音响、运行GATT/WinRT或操作手机；共享内核树、平台配方及旧签名包保持，尚未部署。

| 问题 | 修复 | 验证 |
| --- | --- | --- |
| P1 serdev注销UAF | 关闭回调/新发送入口，等待在途发送/RX，协议退出后释放hdev；同步flush和最终purge | [内核候选](kernel/README.md)：旧版ASan实际复现UAF；新5例并发/退出通过，两个k363对象Werror编译及[完整模块链接](kernel/CONVERGED-LINK.md)通过 |
| P1 GATT日志故障跳清理 | 分离停止/清理状态，诊断与每项资源动作异常隔离，保留共享30秒DBus预算和owner门禁 | [GATT修复](gatt/README.md)：29项实际方法故障注入通过，正常exit0，预期故障保留错误并exit1 |
| P2 IBS分配失败丢重试 | WAKE与idle SLEEP失败均重挂原timer，不伪造ACK或状态 | 保留19例PM回归，新增6例分配失败/ACK/shutdown/close检查通过，零残留skb |
| P2 主机/Windows目录不一致 | 启动SSH前要求central专用私有输出目录 | [主机修复](host/README.md)：实际路径门禁与提前拒绝通过，Windows程序无需变更 |
| P2 RAM地址缓存失败传播 | 显式核对mktemp、写入、DMS与原子发布，失败不继续调用或发布成功回执 | [radio候选](radio/README.md)：旧缺陷负对照；8类故障、成功/缓存命中、双radio锁隔离通过 |
| P2 播放期静音验证盲区 | 读回同一sink静音/低音量，按PID及应用名核对本次stream及路由 | 主机/音频原9例保留；工具内去重后[11项定向用例](host/convergence-validation.json)通过，中途静音、移流、无本次流均拒绝成功 |

完整结果见[validation.json](validation.json)。内核完整补丁同时提供[r0基线入口](kernel/kernel-static-fixes-from-r0.patch)和[PM r2增量入口](kernel/kernel-static-fixes-from-pm-r2.patch)，均零fuzz应用并逐字匹配新候选。RAM helper有独立[修复补丁](radio/radio-address-error-propagation.patch)，不会自动覆盖旧平台recipe。

## 底层收敛与接入归属

修复按故障所属层统一交付，硬件生命周期由驱动保证，原厂身份由平台服务提供，测试资源由测试程序清理。

| 归属 | 收敛内容 | 后续接入单位与当前状态 |
| --- | --- | --- |
| 内核蓝牙驱动 | serdev注销/flush并发、QCA IBS分配失败重试和close收尾，与既有PM r2合成同一份候选 | 仅改`hci_serdev.c`、`hci_qca.c`，已进入同一`hci_uart.ko`和[0.1.0-r3签名候选包](kernel/CONVERGED-PACKAGE.md)。完整链接、183个导入、原363 ABI及两构逐字一致通过；无需增加用户态定时重启或轮询补救。 |
| 平台身份服务 | RAM地址缓存失败传播、私有临时文件与发布核对 | [平台增量接入器](radio/integration/README.md)同步helper、recipe校验和与pkgrel，实际执行前后`package()`，19项载荷仅此helper变化。继续只读取得本机原厂地址并按启动缓存；地址不写死到DT/驱动，也不改NV。当前完整R8平台源集尚未确认，未签旧平台整包。 |
| 测试工具 | GATT异常清理、主机/Windows输出目录一致性、低音量播放期间的本次音频流检查 | 保留单文件GATT依赖和固定摘要；联动器统一`SECONDS`，speaker的pactl/paplay共用同一Pulse客户端上下文。原9例与新增2例通过，10%请求及波形/上限保持。这些问题属于调用者的资源清理和结果判断。 |

接入时只迁移上述受影响源码和helper，复用其它会话届时采用的内核/平台基线，核对对应ABI及recipe后增量构建。这里的k363完整模块证据仅适用于已记录基线，不能直接代替另一内核的模块验证；不整包回灌旧Image或旧平台包。另两会话确认仍为原Image363，本线继续离线，未改变它们的构建输入或设备状态。

r3模块为141800字节，SHA256 `d2a4a90363c7b30b2339ef09c01a4c61670534fae836695a9de989e001c319cc`；APK SHA256 `0e5216fdb3af85125a78bc34888bc253d7044a9de4cd88b71ef03adb9624afcc`。两份APK位于私有`bluetooth-static-fixes-20261023/packages-r3-{1,2}/`。已[验签并实际完成隔离r0→r3升级](kernel/converged-package-validation.json)，确认仅hci_uart模块变化、其余候选文件字节与模式匹配。隔离安装关闭脚本；机型/运行状态为fixture，不能当作现场事务或功能验收。原APK构建器与验证器直接复用，旧r2事务入口不自动适用于r3。

当前GATT服务及其两处调用者均固定新SHA `a1f7c44c8e863bf1fcec9e9e507c4e9d621b0410b17e38b9750f76cae33c9004`。旧实机/协议/构建记录继续属于各自旧版本，原字节私存；新结果不冒认实机通过。已确认身份门禁、Properties.Set的ssv实现、联动调度核心和低音量波形/上限函数未变，复用相应旧范围证据，不重复全量验证。

首次对象编译中两个CC成功，但收尾符号检查漏计模块内符号，且本线generated headers发现旧配置残留。原失败记录保留；验证器修正后复用已保存serdev对象，只补编QCA对象。共享输入及旧产物保持；本线generated headers保留与当前配置一致的同步态，详见冻结[对象报告](kernel/object-build-validation.json)。本轮在其后追加完整模块链接，仅执行composite LD、modpost、模块元数据CC和final LD；58个临时路径恢复且守卫无差异。未构建Image或加载模块。

内核r3已版本化签包，平台helper止于可审查的配方增量和实际staging；两者均未正式采用。真实owner、trigger/index与回退边界仍需后续设备窗口处理。音响物理输入/静音和实际听音仍未确认，以上修复未被认定为此前无声的原因。继续遵守用户暂不进行蓝牙实测的要求，设备顺序由充电/相机会话保持。
