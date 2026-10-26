# 阶段132：MP2650持久节点、真实刷入与完整rootfs

2026-10-12。上一轮已完成隔离源码准备，属于progress；本轮全自动推进静态验证→完整构建→双分区刷入→真实新boot→连续采样及完整镜像。没有人工检查要求，完整系统goal active。

阶段132已实际刷入boot与logdump，内核#132/770匹配模块及UEFI内嵌设备树通过，MP2650在QUP1/0x5c启动自动注册只读标准power_supply。42.13秒8份事件全部非空/ONLINE1/Charging，电压8/8为4.400–4.475V，输入电流7/8为400.00–418.75mA，另1份ENODATA；桌面PID/taint0/BlueZ/5180MHz与11来源保持，窗口无新增故障。新boot仍DPU超时4、BT UART重组错误2，GPU0仅此无负载启动窗口，131迟发CCU故障未修。完整rootfs132含936包/770模块/21,136条目反向metadata与内容零差异、双fsck、encoded UID10000读写及匹配四件套；完整userdata未全量刷入。两份可由稳定130 sparse完整重建的冗余raw删除3.63GiB，130 sparse/source/export和C128/129稳定源码/Image保持。15组功能边界和完整系统goal active。

## 实际补丁与验证范围

E118既有私有ext4卷中power132隔离复制稳定129源码和initramfs；驱动与129逐字节相同，没有新增充电配置写入。QUP1的既有i2c1节点保持400kHz，只新增无label的charger@5c compatible mps,mp2650；没有虚构IRQ/GPIO/电源引用。mps供应商前缀已在当前树。新增binding是本地候选，其示例维护者邮箱是占位值，尚未作为上游投稿元数据。

最初schema最小合法例被拒：dt-mk-schema输入漏了引用的power-supply.yaml，失败证据保留schema-test。补齐通用schema输入后，doc/mk无诊断、1正4反例符合预期，实际板级充电节点无诊断。libfdt逐项遍历新旧整树，仅多一个节点，所有既有节点和属性字节保持；不声称整块板的全部schema已验收。

#132 Image/DTB/770模块完整构建，所有模块可执行段与129相同，vermagic均匹配132，内嵌三个BT模块匹配，console 5:1/0600/root保持，其余cpio内容不变。module archive 92e03906e3f437880590417070640bb0e81fada4638ab2a6dcaf8f57bbae923c。

UEFI必须同步更新内嵌DTB，不能只改FAT中的samurai.dtb。canonical构建与压缩/FV/FFS/Android header检查通过，除DTB外所有可执行模块与实际129 boot一致；原固件源码/FD/FV/boot已逐字节恢复。boot尾部与新FAT仅Image/DTB两文件守卫通过。

## 自动部署与真实启动

新鲜当前129同boot抓取GPT18、NV6/source4/vendor1、persist、770旧模块及桌面/音频/SLPI守卫。首次旧preflash审计要求两个tracer都是0，与现机1/1不符；保留失败，改为记录初始合法0/1并由真正quiesce/freeze强制停至0，未绕过刷入前停止门槛。模块独立放入132 release，不加载至129；旧118/126/128/129目录不删。

BlueZ及桌面停止，DRM无userspace clients且CRTC inactive，PCM closed、双amp idle、所有remoteproc offline、追踪器0、来源/分区/新模块再次核对。fsfreeze成功后一次90 02 OUT收到F1；随后USB read I/O error随设备切换，未重发OUT/重启。fastboot独立核对同设备/product/分区几何，实际boot+logdump写回执通过并reboot。

SSH第16次有界观察恢复，无二次reset。真实#132、新boot身份、完整live DT节点/属性、boot/logdump/persist/GPT18/11来源和全部770模块通过。MP2650由真实DT启动自动绑定，未写new_device；属性0444，uevent有OF身份、ONLINE/status。标准BlueZ已自动启动，Phosh/Phoc和DRM/card1恢复，console warning0。

连续8样本42.132秒：ONLINE8/8=1、status8/8=Charging、电压8/8=4.400–4.475V、电流7/8=400.00–418.75mA，1份errno61 ENODATA，事件不丢。桌面PID不变/taint0/BlueZ running/Wi-Fi5180MHz，窗口所有故障计数增量0。新boot累计DPU frame done timeout4、UART reassembly2、GPU fault0；未施加GPU绘制负载，不能宣称GPU/持续显示修复。Charging是芯片状态观测，不是本机充电控制、功率预算、ADC外部校准或保护策略验收。

## 完整rootfs与空间

从已验130完整模板复制所有内容/类型/uid/gid/mode/link/xattr/devices，替换为唯一132 release的770模块，仅修改两个stage标记，936包/BlueZ DMS服务/default symlink/AutoEnable false/双频Wi-Fi profile/凭据/固件/UID10000 home保持。F2FS正确设备节点编码、稀疏完整payload与skip holes重建、两份raw只读fsck、21,136条目反向导出内容metadata零差异和encoded真实降权读写unlink通过。rootfs generation数值元数据首次沿用130，已修正生成器和finalize，重新只读验核，不重打包/刷入。

新rootfs sparse 1817953892字节，SHA 290e7af5fdda219a558032f4f75dfec6979a32e66693f117964361a4fd903ccb；boot 501074e6feb3c5e93eff86f40848acbfc102da44e06cf52f95770d80a83d07f6；logdump db6b966975b987cd51e91f9488185b0a5e4a557755cc3b7043f0e6550aa19751。四件套完整且hash实际重算，软件镜像可部署，完整userdata未bulk刷入/擦除；内核/设备树补丁与模块已实际部署。

两份130 raw逐一通过当前130 sparse全payload和空洞重建证明，inode/dev/size/mtime及无loop挂载重验后unlink，删除分配3895017472字节，无递归删除。稳定130 sparse/source/export保留，最新132 raws/export/template保留。C128/129 Image新鲜hash及源码/config保持，C未知旧对象不删，原WSL VHD未resize/compact。当前E118 inner余2188591104、E129 inner余1435234304；主机实际空余以host-space-validation.json为准。

## 下一项和失败边界

MP2650持久观测缺口已关闭，完整充电控制仍须补齐。已再次检索[MPS官方产品页](https://www.monolithicpower.com/en/mp2650.html)及[官方datasheet](https://www.monolithicpower.com/en/documentview/productdocument/index/version/2/document_type/Datasheet/lang/en/sku/MP2650GV/document_id/9664/)，下一轮核对本机原厂输入预算、2719/短路保护、热敏/NTC和battery limits，形成明确寄存器及恢复契约后实现/有界实测；不能直接拿eval-board或其它板默认值当本机配置。GPU131转储/CCU映射生命周期、DPU4/UART2另留档，避免重跑33场景/全桌面debug。15组中的物理camera/PM8008、GNSS真实fix、蜂窝数据/通话、指纹、休眠等继续开放。

所有一次性prepare/build/stage/quiesce/flash/collect/cleanup脚本均已实际执行，不重放。依赖工具生成与staging审计曾并发，导致一次verify脚本尚未生成，模块实际staging已经成功；后续只补审计，没有重放staging。私有现场仅E:/edk2-samurai-out及手机/var/lib/samurai，公开只保留统计与artifact hash。

收尾实际关闭E118/E129：同一次WSL确保真实挂载身份，sync/卸载后无loop、离线只读e2fsck均0；E122/126仍未挂载，原WSL VHD不动。全部作业terminal，最终同boot/原桌面PID/taint0/BlueZ started/永久MP2650 bound通过，GPU0/DPU4保持。公开审计覆盖最后新增关闭与状态文件，不把仍开放的15组完整功能标为成功。
