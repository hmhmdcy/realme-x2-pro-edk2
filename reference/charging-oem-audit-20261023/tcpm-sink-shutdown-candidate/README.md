# 固定受电 TCPM 收尾：507 R2 实测未通过，已自动恢复506

2026-10-25。R2已实际写入启动，原key/NCM自动恢复，Type-C port/partner注册成功；但默认Rp连接的TCPM current_max/current_now均为0，验收两次失败，未采用。原USB输入仍为500mA、保护健康。300秒恢复器自动还原506并重启，原载体/文件/模块/预算及四PD控制两次为0均已核对。[实测结果](phone-trial-result.json)。R1仍禁止stage、从未安装。下面的“暂存/未安装”描述为试运行前记录。

原full-TCPM shutdown没有关闭动作；原pdphy_stop只关闭IRQ/reset work、清TX/filter及放电源引用，没有明确清EN/BIST。本机native DT实际PDPHY与USB2共用L2（phandle0xc0），所以放引用不能作为PD关闭证据。依据原厂qpnp-pdphy close已有的BIST/TX/EN关闭顺序，以及实际主线IRQ、TCPM unregister和CC debounce实现补齐本分支，没有新私有DT开关、虚假电源或桌面改动。

实际[补丁](shutdown.patch)仅为准确Samurai/PM8150B、固定sink/device、单个5V500mA PDO和2.5W的配置启用新收尾。先结束CC IRQ/工作、PD IRQ/reset work，保持PDPHY供电引用，调用真实tcpm_unregister_port结束协议回调；然后依次清BIST/TX/filter/EN并检查每次读回，成功后才放供电引用，最后再次join可能由剩余TCPM回调排入的CC debounce并恢复SNK_ONLY。receive_work在这个固定源中未使用/未初始化，没有对它调用cancel。

PD写/读回错误保留第一个错误，继续尝试其余关闭零值，保留供电引用并将CC设为disabled，不自动重试；调压器或CC错误也保留。重复shutdown/remove不重入MMIO、不重复put。PD启动失败则把已取得的引用保留到TCPM join之后收尾。未启动的资源不虚假宣称PD已关闭。这是本5V试运行的收尾，**不是9V合同降回5V的实现**；完整PD/APSD共存、合同预算和高功率仍需后续实现和实测。

[七组关闭测试](shutdown-test-result.json)直接执行十五个完整真实函数，建模kernel/device/IRQ/work/TCPM/regmap边界，覆盖每个关闭写、读错/非零、供电失败、CC失败、启动失败、真实join先后、重复调用及原PD5V/default分支；ASan/UBSan、Werror通过。[原四组受电测试](test-result.json)保持通过。[源码复核](source-review.json)确认33个原完整函数逐字保持，仅六个原函数改变、五个新函数；[五对象](build-result.json)及[Image](image-build-result.json)W=1零诊断。配置、电量计、initramfs、builtin元数据及全部导出保持。

核对实际tcpm_reset_port后，纠正了注释/测试中对最后一次debounce来源的描述：来源是join期间剩余TCPM工作，不是reset_port直接调用CC。[重编比较](comment-correction-reuse-result.json)的五个对象逐字相同，因此复用已有Image/FAT，未重复链接或传包；首封装材料保留于history。

| 试运行产物 | SHA256 |
| --- | --- |
| Image507 R2，59,439,616字节 | 371493db3a9cbd72af6c37bc5ea2f7637ee5fc0dcb8d46c4ac24550599dc082e |
| boot（复用相同BDS/native DT） | e48dddfc2ae0beda4a128f878cabb54c63dbaad7e9d4ad0cab9500fc9bc2c100 |
| FAT/logdump | 3ebf72dedf5ca39ff2ec24cbe491e7c2f5c8c080c753cbb68c4c602b886a7f5c |

[FAT包装](logdump-package-result.json)使用已有mcopy路径，容纳新增64KiB；只有Image的数据、分配及目录改变，其余文件/字节保持，读回与fsck -n通过。[boot](boot-package-result.json)复用前版精确载体，无需重新构造固件。试运行仍暂禁EUD-route/APSD borrower，只申请5V500mA，不能直接采用为正式配置。

[独立暂存](staging-result.json)：phone `tcpm507-trial-20261025-02`、host private `image507-sink-trial-private-02`。旧boot5c8d/FATb29e和相同新boot从未执行过的R1缓存建立硬链接，新FAT另存；meta/文件/两载体均校验，live文件与分区未改。trial manifest04542f…a5fe，guard ad5157…e59e。[ready](full-pd-shutdown-ready.json)只代表软件已验证可开始有界试运行，hardware_verified=false，不作为实机通过。

[stage](trial-stage.py)保留实验收尾/健康AUTO/电量/进程门，并要求ready匹配实际新两载体。首次新boot用[audit-phone.py](audit-phone.py)加`--carriers`查询实际绑定/同一TCPC的port、partner与供电属性、两样本原USB500/健康、真实恢复进程/锁和两载体。该入口不控制充电、不查询/rearm MAC、不写accepted。新系统不接纳，统一等待300秒guard恢复原boot、FAT及原rootfs后重启，host不并发restore；恢复依赖Linux用户态能运行，不能恢复用户态前的硬挂。

故障定位：实际CC状态0x1506=0x08（默认Rp），固定TCPM的tcpm_get_current_limit在此分支需要TCPC get_current_limit回调，而QCOM端口未提供，故返回0。下一步接入实际USB供电预算及其变更通知，不能填固定500mA来通过验收。PD合同、物理VBUS断开、APSD传输及USB物理唤醒仍未通过。恢复后[预充03](../../charging-management-20261023/precharge-live506-r3-result.json)继续，不再重放本R2事务。

实验是否观察到预充另按原结果验收，未通过仍保留为未通过；后续短测要求它已收尾且没有采样/恢复错误，不将另一项测试必须成功作为额外刷入门槛。
