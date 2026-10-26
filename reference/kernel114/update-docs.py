from pathlib import Path

root=Path('/mnt/e/RealmeX2Pro edk2')
summary='''[阶段114](sessions/114-complete-rootfs-and-qmi-ipa-foundation.md)，[继续检查点](NEXT-SESSION.md)。

2026-10-12持续适配已恢复，完整系统目标仍active，只进行自动化调试，不要求人工检查。新本机专用F2FS sparse rootfs已生成：1,783,174,616字节、936包，逐块展开比对与源/重建两次fsck通过。镜像未刷入；当前手机通过签名APK已补入同批应用/诊断工具，原Phosh/greetd/UCM、NV6/source4保持。仍运行#113/boot15，DPU累计9/GPU故障1/taint512；新安装窗口未新增故障。

原生QMI四项只读查询和LOC三项只读查询通过；55秒GNSS start/stop窗口没有位置/卫星/NMEA事件，停止回执已取得，定位未验收。隔离#114源码准备共享IPA v4.1驱动与禁用SoC节点、ZRAM/SYN_COOKIES，完整构建进行中，未上机。rootfs用户态补齐不等于15组硬件全部可用，显示/GPU、完整传感器、蜂窝数据/通话、定位、摄像头、指纹、充电及休眠等继续推进。原始日志/身份/固件/镜像保留私有。

'''
p=root/'README.md'; text=p.read_text(); i=text.index('Unofficial EDK2/UEFI port'); p.write_text(text.splitlines()[0]+'\n\n'+summary+text[i:])
p=root/'FLYWHEEL.md'; text=p.read_text(); i=text.index('> 2026-10-08 建立'); p.write_text(text.splitlines()[0]+'\n\n'+summary+'持久F2FS正常重启仍需当前boot守卫、音频/ADSP/无线完整排空和sync；F1前需同次启动的freeze或只读卸载证明。旧boot14守卫无效；当前taint512不能套用taint0守卫。新rootfs已构建，不使用会erase userdata的旧flash-pmos.ps1进行日常更新。\n\n'+text[i:])
p=root/'linux-port/docs/HARDWARE-STATUS.md'; text=p.read_text(); i=text.index('| 功能组 |'); new=summary.replace('sessions/','../../sessions/').replace('(NEXT-SESSION.md)','(../../NEXT-SESSION.md)'); text='# RMX1931 Linux 硬件接入清单（2026-10-12，阶段114）\n\n15组硬件保持。\n\n'+new+text[i:]
text=text.replace('自动MPSS、QRTR及固件/RAM COW运行；6个源NV保持','自动MPSS/QRTR/COW运行；原生QMI DMS/UIM/NAS查询通过，NV6/source4保持；Calls/Chatty已安装')
text=text.replace('| GNSS定位 | 未验收 | 本机固件/调制解调器接口、用户态和实际定位 |','| GNSS定位 | LOC三项只读查询、start/stop回执通过；55秒窗口无位置/卫星/NMEA事件 | GNSS实际定位、持续事件、定位服务与桌面集成 |')
text=text.replace('下一项完成大请求RAM传感器试验，并继续重启、5GHz、显示长稳和其它硬件；','下一项完成隔离#114离线构建与IPA同机资源/固件核对，继续重启、5GHz、显示长稳和其它硬件；')
p.write_text(text)
p=root/'DOCS-INDEX.md'; text=p.read_text(); text=text.replace('当前：[阶段108]','当前：[阶段114](sessions/114-complete-rootfs-and-qmi-ipa-foundation.md)、[继续检查点](NEXT-SESSION.md)。历史：[阶段108]',1); p.write_text(text)
(root/'NEXT-SESSION.md').write_text('''# 继续检查点：阶段114（2026-10-12）

完整系统goal active。按用户新要求继续自动化适配，不重复阶段113“收尾后停止”的旧约束；不要求画面、触摸、遮挡、转动或听音人工检查。长期无进展问题保留文档/证据后转项。

先读[阶段114](sessions/114-complete-rootfs-and-qmi-ipa-foundation.md)、[15组状态](linux-port/docs/HARDWARE-STATUS.md)及reference/kernel114的镜像、实机用户态、QMI、LOC、GNSS核验。

现有手机仍#113/boot15、taint512、F2FS rw、Phosh/Phoc运行；DPU累计9/GPU故障1，稳定性未修复。SLPI offline/供电0，原selector和launcher保持；PCM closed、双功放静音；NV6/source4保持。已经原生安装936包，包括新Calls/Chatty/Firefox/Megapixels/QMI/libcamera/诊断工具，没有刷机、erase或重启。

新镜像E:/edk2-samurai-out/kernel114/samurai-rootfs-f2fs.simg已生成，1,783,174,616字节，展开119,033,245,696字节。SHA见reference/kernel114/rootfs-image-validation.json；源/重建fsck及逐块展开比较通过。该镜像含本机身份/固件/凭据，不公开；配套当前#113模块和既有启动身份。镜像没有刷入，不需为部署应用覆盖现有userdata。

原生QMI DMS/UIM/NAS查询通过，LOC控制查询/start/stop通过，但55秒无定位/SV/NMEA事件；停止回执已取得。ModemManager无modem、无蜂窝netdev。第一条LOC失败是不存在的CLI选项，不能当modem失败。

隔离源码/home/cy122/pmos-samurai-kernel114/{kernel,initramfs}：IPA v4.1驱动/shared SoC节点已移植，节点禁用，排除Hotdog板级变化，ZRAM/SYN_COOKIES准备。参考源码固定47087509c4289c2580c54f5433e55366b2e00445，文件哈希在私有primary-reference/source-manifest.json。完整Image/modules/DTB构建日志在kernel114/kernel-full-build.log；若有活动构建先检查进程/产物，不重复启动。

下一步完成并记录构建，再核对本机Realme下游source/arch/arm64/boot/dts/19781与qcom的IPA v4.1资源、IMEM/时钟、stock IPA固件/loader mode和SSR有界等待。未证实资源不启用设备。还需解决OpenRC zram provide swap与真实swap同名冲突；elogind DBus有daemon但OpenRC failed、iio-sensor-proxy缺SSC，避免重启当前登录会话只为清除failed状态。

真正部署#114前设计当前boot15/taint512的守卫，按已验证流程排空GUI/用户音频/功放/ADSP/无线/MPSS、核验NV、sync后正常重启。F1需同次启动freeze/只读卸载证据。旧boot14/taint0脚本不可原样重放。#113当前boot/logdump必须成套保持匹配内嵌DTB，原回退111 boot+112 logdump仍有效。

没有任何私人身份/日志/固件/定位或镜像公开、提交或推送。所有应用安装与短窗口通过仅证明其限定结果，完整硬件goal不能标为complete。
''')
print('STAGE114_DOCS_AND_ALL_15_HARDWARE_GROUPS_UPDATED')
