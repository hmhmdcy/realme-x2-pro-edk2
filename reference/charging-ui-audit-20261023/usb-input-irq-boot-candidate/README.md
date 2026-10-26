# USB IRQ native-DT 启动候选

唯一 host-only 封装已通过，未部署。新 boot 为96MiB，SHA `eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06`；私有文件为 `E:/edk2-samurai-out/charging-management-20261023/usb-input-irq-boot-private-01/boot-usb-input-irq-private.img`。本叶没有构建Image／SDK／BDS、rootfs包、R9部署cohort、手机事务或新现场guard，也没有改已prepared的502 logdump-only事务。

## 最小封装与实际结果

基线是实际当前501 boot `97811cc4…c67f695`，原BDS EFI为 `071a628b…dcc196b`，内含原精确UTF16 `bq27xxx_battery.samurai_instant_current=1`。只将完整 native-DTB FFS 的 raw payload 从 `9271d9cc…0914358` 换为已通过全树对照的 `13d359c4…8adee9f`；保持其type／attrs及raw section类型。其余100个完整FFS（含BDS）、BDS全部section和参数逐字保持。

复用已冻结 kernel104 FV／section parser，以及原501封装器的 `raw_files`／`extract_current`／Android-ID函数实际原文。没有运行旧封装入口或旧baseline helper的顶层shared固件输入读取。INF和pre-rebase SEC／EFI／map直接复用当前501私有执行原件；五个原GenSec／GenFfs／GenFv／LzmaCompress／gzip工具均核原SHA。压缩方式、regular fd0、FLG0、原reproducible mtime、default GenFv原样，未使用旧失败的 `-F FALSE`。

原compact／gzip已通过的逐字复现收据仅作来源复用，不再执行；本轮新范围是DT单FFS替换及完整新boot重解析。96MiB boot只流式摘要，按seek读取header／约6.7MiB payload／ramdisk，尾部按1MiB复制及比较；没有整文件read_bytes、副本重压策略、资源清理或WSL配置变更。

实际唯一exec9554已终态0，10条host工具命令全部wait同child并终态0。native DTB增加188字节后，原压缩流程自然得到kernel payload6680318B（原6680472B），newused仍为6684672，原绝对tail边界没有放宽。页内余量为258B；不能将这次压缩大小变化另称为算法优化。32MiB mainFV完成后与写出boot重解析后，都要求只有DT FFS变化；完整SEC及0xfe8位置、container位置、compact FV header、144字节shim、compat、ramdisk page和绝对tail全部保持。Android v1 header只允许kernel_size／ID变化，并先验原ID、写后再验新ID。

`result.json` 绑定全部真实命令／PID／终态、原件与新产物摘要、写后全解析和parent输入／mountinfo保持。所有原件保留；输出目录已存在则拒绝重放。默认 `package-boot.py --check-local` 只核原输入和工具摘要，不调用封装工具或设备。

## 必须配套的未来文件，尚未生成包

新boot含IRQ DT，必须配相邻已冻结 `usb-input-irq-board-candidate` 的新去重USB ko：`7cbf10c0…c94ff5f`，87832B。新DTB不能单独配旧R7 ko。现三组件结构保持：R8 charger `10ec06fb…6297f`、protection `75b97e0d…783c7`不变，仅USB provider替换。已证明的最小rootfs文件集合是：

1. 原目标路径 `/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko` 的新字节；
2. `/usr/share/samurai-charging/manifest.json`：以原R8 `320316c3…c10a1f`为底，仅USB module摘要、installed_files同路径摘要和未来明确revision变化。所有其它条目、900mA／250mA帽与source-budget标记保持。

服务来源是已实装61451ff…管理器、原OpenRC和两个依赖。`verify()`按manifest校验磁盘，`load_module()`显式同一路径insmod并比对resident note；OpenRC仍 `after udev samurai-usb`。新driver看到唯一enabled DT node会跳过软件board创建，因此现 `register_board=1`加载方式可复用，不需改管理器／OpenRC／autoload setup。`native_retained`原逻辑和DWC `usb-psy-name`保持。现 `/usr/local/sbin/samurai-usb` 的500启动SHA `2a364e12…5b9a54a`及平台recipe不在变更集合；不把旧仓库100脚本当当前运行源替换。

本叶只记录上述最小变化方案，没有创建manifest新字节／tar／安装器。未来若纳入另一个已审只读protection采证版本，应另冻结相应完整cohort；这里不预先命名或锁定R9。外部FAT DTB A823和logdump／Image都不在本次封装写路径。

## 未来stage与回退边界

可复用原R7两文件stage的原子写／fsync／已知状态回退算法，前置必须改成届时实际boot／guard／健康或合法Full状态，不能照抄旧r6 FLOAT占位前置或旧常量。先对原R8 manifest及三件resident note做fresh核对、持原service flock、直调原manager同步INHIBIT并读回，再备份／替换两文件；不热卸DWC仍持有的旧provider，不发AUTO。

stage后磁盘是新ko／新manifest，但live仍旧R7 note。这只能叫 `staged/runtime_pending`。当前管理器对新磁盘 `verify()`可成立；resident USB必须和备份旧ko比对，不能 `loaded_matches(new_file,old_resident)`。未来quiesce／restart／adoption须有**独立新guard**同时绑定新磁盘、旧resident、stage终态和boot-only候选；不能重用已prepared502的R8常量与事务或把文件改好当新runtime已生效。

未来回退集合为该事务原boot97811、旧USB ko7d4e0f…c4f70与原R8 manifest320316…c10a1f；logdump保持该次未来preflight实际采用的精确值。原502通知事务若先完成并adopt，未来IRQ事务须采用它的新boot／Image／guard事实；本叶不把预期502成功当成已发生，也不改其已绑定payload。新boot与两文件必须成组核定后才允许候选重启；部分／未知写入只核原child和真实文件，不重发或盲回退。旧文件恢复且匹配、原boot恢复并确认后才能走原系统启动路径。

后续验收还需要同一新DT/provider真实probe、两条命名IRQ真实注册、物理拔插中断计数／事件时间变化，并保持保护、source/native预算和硬件限值。两IRQ查找均absent时legacy 1秒poll仍可能成功，加载成功／新DT存在／Online变化均不能单独当IRQ或图标时延通过。本叶未访问手机，不授予APSD／PD／role／route权限。
