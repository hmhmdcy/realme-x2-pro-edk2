# Current IRQ + native USB PM budget pair

本叶只离线生成两文件增量：USB `7cbf10…ff5f` → 已实际构建的 IRQ+PM `d04608…7037`，以及当前原始清单 `18e8a1…b4e5` → `34ead4…a39b`。清单仅两处 USB SHA 和独立 revision 的字节改变，反向替换必须逐字恢复原件；charger `97c16…8ffdd`、保护 `7848cf…3044`、6145 服务、500 startup、900/250mA 请求及源预算规则保持。没有 installer、host transport、guard 或实际设备请求。

配套必须保留当前 boot `eddade…6e06` / IRQ DT `13d359…dee9f`，使用已完成的 Image504 `f6477d…a3f4` / 64MiB logdump `4453d4…6d83`。FAT 原件与完成收据从[既有 Image504 载体](../../charging-oem-audit-20261023/image504-budget-logdump-candidate/README.md)复用；本叶不重新封装它。原非 IRQ 的 2691/f74a 包不能用于此组合。

默认 `python -B cohort.py` 只核固定来源；`check-local` 核真实完整材料而不创建 OUT。唯一 `build --execute` 已完成，原工具输出 `9d758d` exit0，build PID243104 和随后只读 audit PID237908 均原 Popen wait0。私有目录为 `E:/edk2-samurai-out/charging-management-20261023/irq-native-usb-pm-budget504-cohort-private-01`；存在即拒绝再次物化，失败原件保留。全部产物 SHA 见 [payload-result.json](payload-result.json)，完整配套声明见 [cohort-manifest.json](cohort-manifest.json)。

[module-binding-test-result.json](module-binding-test-result.json) 是新增 3 组实际模块完成/来源绑定测试；原 5 组清单及当前 tuple 测试没有重跑，原受测源码和收据保存在 `history/current-tuple-5-tested/`，4 个受测函数体逐字不变，见 [source-reuse.json](source-reuse.json)。archive/check_archive/validate_carrier/module_identity 直接引用固定旧纯函数，不重跑旧打包、模块或大矩阵。当前旧 identity/cohort 打包收据实际记录 7 例，native 包与 carrier 绑定分别为 10/4 例；不把这些历史次数标为本轮新执行。

本轮完整回退是包内原 USB7cb + 原 manifest18e8，再配原 logdumpace2，并正常启动对齐磁盘与驻留身份；bootedd、97c、7848不变。单退 Image 或调用 manager 的 charger rollback 都不等于此回退。provider 自持引用，不能热卸；新磁盘与旧驻留 note 不同期间不得调用原 start/resume 伪造对齐。暂存只可报告 `staged/runtime_pending`。真实 504 启动、IRQ 和 PM link/回调顺序、预算撤销及重新授权、NCM/严格密钥恢复仍未验收；不覆盖 auto/direct_complete、完整 UDC/DMA 或 PM unwind。
