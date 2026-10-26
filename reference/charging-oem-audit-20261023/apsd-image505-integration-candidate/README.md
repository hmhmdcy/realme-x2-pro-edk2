# APSD505成套内核、固件与设备树

后续当前版本为[Image506跨待机修正](../eud-route-pm-candidate/README.md)；本页保留505阶段及其完整504逆向。

2026-10-25。成套Image505、BDS、native DTB、USB KO和builtin元数据已实际安装并启动采用，**普通SDP500mA和RTC待机恢复通过**。当前505/USB161b/chargerbef4/保护f6bef/服务83469/manifest8b402；桌面保持原版。后续实际组合以`assembly-inputs.json`为准；`composition.json`保留内核构造时的组件和初始固件来源，实际固件另增加当前瞬时电流参数和5V模式参数。

| 实际私有产物 | SHA256 | 字节 |
| --- | --- | --- |
| Image505 | b91a5a667d55c34d9f8fc5aa515161c7e824b20b167be2415a982e96fa949d43 | 59374080 |
| BdsDxe.efi | 939345bc6bb9f114e77da614e33e36d5bd4bfc59f8c17d3bc547bf2f35084f0b | 110592 |
| native DTB第二版 | d5fa6cabdd231fed8e35b26cb17e8d4c59068705d90285775b7ede48f2e338d3 | 116626 |

`prepare.py`以实际363公共基线进行三方合并：APSD的DWC窗口/生命周期与已经装机的Image504预算/PM修正没有共同改动的函数，合并后两边相关函数均逐字保持。共34个内核输入直接复用已检查组件，包括三个真实EUD producer、EFI交接、route provider、实际owner、PHY撤销及PD5V。沿原编译缓存，仅在私有overlay copy-up视图中写入和构建，原504下层和共享目录均未改动；initramfs只读绑定，不再完整复制源码和旧构建。

[真实Kconfig准备](kernel-preparation-result.json)完成后九项配置变化，原内建全部保留；Type-C TCPM、PMIC及qcom EUD转builtin，自动选择所需HPD桥，新APSD/route配置显式开启。首次受影响对象构建因两个目录缺少本地头文件失败，返回2/外层1；原记录保留。补入三个原有头文件后，[实际增量构建](kernel-build-r2-result.json)受影响对象3.10秒、Image46.76秒，两个原make进程均终态0、日志零warning/error。原15097条builtin导出行全部保持，新增21条；原BQ对象、release及initramfs完全相同。此为链接/构建兼容证据，尚不是新组合的模块加载或实机证明。

[设备树首版](dtb-and-command-result.json)复用实际已装机13d359 IRQ native DTB，只修改必要phandle、route/Type-C接线、Type-C显式5V供应和chosen参数，其余全部原始属性、保留表和boot CPU保持。EUD硬件节点仍disabled，供应phandle与实际PHY的vdda33完全相同。整合后从真正Image505的参数表确认命名空间为`qcom_pmic_tcpm.samurai_5v_only=1`，[第二版](dtb-and-command-r2-result.json)据此修正初稿的源文件名前缀；初稿未安装，旧源和DTB保留。BDS与DTB都保留当前实际`bq27xxx_battery.samurai_instant_current=1`。

[实际BDS构建](firmware-build-result.json)只重编一个对象、替换一份library，并复用其余40库完成DXE链接和GenFw。原后处理因非空stderr停止，但原链接返回0；只审原缓存，不重放编译或链接。规范化后的串行LTO和中间ELF RWX提示与原已通过R2相同；最终ARM64 PE32+ boot-service driver节权限与原R2相同，`.text` RX、`.data` RW，无最终WX节，实际命令行存在。

[USB模块R2](input-module-build-r2-result.json)为161bcc/26128B，实际505导出满足53强导入，W1/Werror零诊断。仅初始化值按新配置默认启用APSD，其余函数逐字保持；原服务直接insmod，未修改服务主体。旧默认关闭版本保留。四份[builtin索引](builtin-index-result.json)来自实际505；手机隔离根9次modprobe dry-run通过，全局dep/alias索引保持。最终实机加载的是R2，实际note匹配。

[启动载体](boot-package-r3-result.json)为5c8d23/96MiB，仅BDS和DT两FFS变化，其余99完整FFS、SEC、shim、compat及原绝对尾部保持。首次几何拒绝和仅重压缩的第二次拒绝保留；第三次直接复用缓存gzip，并证明相邻页本来就是完全相同的换行ramdisk及零填充，因此未改原尾部任何字节。[FAT载体](logdump-package-result.json)为b38826/64MiB，只替换实际Image，读回/fsck及其它全部文件保持通过。

[真实安装与采用](phone-activation-result.json)先FAT后boot，均实际块设备写入/fsync/读回，再装八个暂存文件，正常重启；NCM与原key自行恢复，真实EFI路由和5V Type-C provider绑定。普通源/native/硬件500mA、CC250mA/整包8.725V与保护Good通过。新外部KO带正常O taint4096，未出现warning/oops taint。主服务83469和原OpenRC入口最终保持；临时boot guard已删除，最终rootfs只有USB KO、四builtin元数据和manifest六处变化。

[本组合RTC](phone-rtc-result.json)驻留15.1946秒，success+1/fail0；所选12条PM callback end全部err0，原key/NCM与预算/保护恢复，无新增fault，alarm和独立trace清理、worker3704终态0。未发MAC查询或rearm，当前缓存0/0及cc134保持。首次采用源因主机生成字符串语法失败，任何手机语句均未执行；改用原始字符串后通过，原失败私存。

[精确逆向](inverse-result.json)保留原edd/4453及七个原rootfs文件，恢复顺序先原boot再原FAT再原rootfs。五分钟无人值守试运行guard已完成接纳并正常退出；它依赖Linux用户态，不能覆盖pre-userspace硬卡死。采用后恢复原OpenRC并删除临时guard，后续正常重启没有新接纳倒计时。重启实际UFS名称由sdd变sde，已将保留恢复器修正为[稳定分区UUID/起点/大小/编号](recovery-identity-result.json)，当前两分区无写入检查通过；尚未实际执行整套逆向。不得重放任何终态构建、stage或测试。

本候选的route证据仍在首次PM prepare过期，尚未实现路由跨待机重建；实际首次物理断源、新连接APSD/FLOAT、完整Type-C/PD及快充仍待验。源码与模型测试不替代这些实测。[当前504组合回满观察](../../charging-management-20261023/charger-full-return001-result.json)也已实机通过，377样本及稳定Full40.947秒，原worker24901终态0/已退出，AUTO Full/锁释放fresh确认；已无此观察器占用手机。
