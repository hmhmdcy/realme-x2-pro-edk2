# 完整 hci_uart 离线链接收敛

2026-10-23。原 `source-lock.json`、README、对象/host 回归报告保持冻结。本次只增加完整模块链接、strip 和独立 ABI 检查，不重复已通过测试；包交付见主线维护的 `CONVERGED-PACKAGE.md`。

采用既有两个已验证对象，并将其 SHA 与对象报告逐字核对。其余七个成员/提供者对象保持原件；Kbuild `-o` 将九个已验证输入标为无需重编，强制仅重新链接 hci_uart composite。btbcm/btqca 小目标用于 modpost 解析提供者，最终包仍由主线复用原两个模块。

实际执行 PID 2668，`-j1 W=1 KCFLAGS=-Werror`，5.942 秒 exit 0。日志仅有 composite LD、MODPOST、hci_uart.mod.o 元数据编译、final LD，没有成员对象重编或诊断。未编 Image，未打包/安装，未访问手机、SSH、WinRT、射频或 SDK。

| 产物 | 字节 | SHA256 |
| --- | ---: | --- |
| hci_uart-static-fixes-k363-intree.ko | 851840 | `ace953c9e51bce3d1f28011c171a7369b79784b216af6bd459ffc24f1e1c36ee` |
| hci_uart-static-fixes-k363-intree-stripped.ko | 141800 | `d2a4a90363c7b30b2339ef09c01a4c61670534fae836695a9de989e001c319cc` |

私有目录：`E:/edk2-samurai-out/bluetooth-static-fixes-20261023/kernel/converged/`。日志、原 363 Symbol 表副本、完整导入记录、备份/恢复清单与终态均在同目录。

核对结果：模块名 hci_uart、intree Y、vermagic `7.3.0-rc6-rmx1931-samurai-k363+ SMP preempt mod_unload aarch64`；仅依赖 btbcm/btqca。183 个导入全部存在于原 363 `Module.symvers`，4 个导出逐字段一致；模块结构 1152 字节，与旧 r2 相同；alias 相同。原 Image363/config 的完整 SHA 同时核对，未将 source354 当前 HEAD 当作运行内核。

原 363 为 `CONFIG_MODVERSIONS=n`，因此无 CRC 强制校验及版本 section；报告没有把符号/结构核对称为启用 CRC 的运行验证。strip 保留 build ID `df2022239015d8fcb97dd05478d7cfec5591b3e6`，本轮模块未附内核模块签名，APK 签名由主线负责。

写入前已保存 58 个受影响路径：两个源文件及 symlink 类型、9 个成员对象/.cmd、三个模块的 .ko/.mod*/.cmd、Module.symvers、modules.order 和其它模块索引、module-common 对象。完成后逐字及类型恢复；共享源码/构建输入、原 config/headers、旧本线对象/模块、旧 E 盘产物全部守卫一致。没有卸载挂载点；本线持有的空闲常驻 shell 已按主线要求关闭。

固定输入、脚本和输出见 `converged-source-lock.json`；真实链接与全部导入记录见冻结的 `converged-module-validation.json`。实机验收仍由主线在用户允许的窗口另行安排。
