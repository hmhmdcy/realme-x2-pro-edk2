# 176：WCD934x 复位后地址刷新与重复绑定回归

2026-10-14。已部署 kernel176/logdump176，保留 boot/DTB172、modules/software132、Mesa149、UCM173。扬声器和麦克风主通路已可用：171用户确认两组测试音来自手机，本轮原生ALSA及普通用户PulseAudio左右声道也重新通过声学闭环。176进一步修复175父设备硬复位后的地址缓存和probe失败清理，两个codec、八个MFD父设备卸载/重新绑定全部自动恢复声卡，无NACK/读超时。完整音频goal继续active，实物耳机、系统休眠/SSR和音质等仍待验。

## 问题与实现

175第二次父设备绑定出现NGD `0x82000000`、MC0x60读-110与WCD bring-up失败，后来又探测成功；该历史失败保留在[175](../kernel175/README.md)。硬复位后main和interface两个SLIM设备仍可持有valid的旧logical address，`slim_get_logical_addr`会直接返回，不重新查询。176[增量补丁](reset-address-and-probe-cleanup.patch)修改四文件：

- MFD保持600us电源就绪和20ms/20ms复位延时；复位后通过`slim_report_absent`失效main和sidev地址。主地址查询放在私有状态锁之外，避免查询触发UP通知时递归加锁；ready门控使早期通知defer，查询成功后才执行芯片初始化。
- 把现有exported absent API声明移到公共头文件。core在controller锁内检查地址此前是否valid，只在非controller分配地址且确实valid时释放IDA，重复失效不会重复释放。
- MFD电源disable和status清理由devm action管理，覆盖client probe成功后SLIM bus wrapper的地址获取再失败这一段。status先移除子设备、IRQ domain与regmap，再释放GPIO、电源和regulator引用；正常remove与action重复调用也保持幂等。

175的jack、interface regmap和MCLK生命周期修复，174端口IRQ停止修复，168 NGD/messaging，172 DTS/MBHC与173 UCM均保持。没有通过增加复位sleep、循环bind或改功放增益来取得结果。实机没有可用dynamic_debug/ftrace函数跟踪，因此没有运行时地址查询轨迹收据；源码、函数级负对照及实机复位结果支持本轮修复，不扩大为所有复位时序故障都已排除。

## 来源、构建与部署

此前[171](../kernel171/README.md)已核验Realme原厂19781音频overlay及OnePlus 7T Pro补丁，从中确认SD1/GPIO140；本机MAX98937与一加TFA9874不同，寄存器和增益没有套用。本轮又读取[上游MFD](https://raw.githubusercontent.com/torvalds/linux/master/drivers/mfd/wcd934x.c)和[SLIM core](https://raw.githubusercontent.com/torvalds/linux/master/drivers/slimbus/core.c)：取得的MFD复位路径未调用absent/address API，core的absent函数没有was_valid判断，core内容哈希与本轮修改前一致。[来源收据](upstream-source-recheck.json)记录UTC、内容SHA256与URL；GitHub commit API返回rate limit 403，master内容以哈希固定，不冒充固定commit或完整上游搜索结论。外部代码仅阅读，没有执行。

[函数级验证](host-tests-validation.json)共71场景：地址25、MFD probe46，包括20轮16线程重复absent、13个I/O失败点、查询中的早期状态通知，以及真实SLIM bus wrapper在client probe成功后失败的devres清理。ASan/UBSan通过；重复IDA释放、main/sidev旧地址、缺ready门控、缺电源清理、缺status清理六个负对照均被拒绝。fixture模拟硬件改变逻辑地址；不能把模拟结果单独当成物理根因测量。

[构建收据](build-package-validation.json)：W=1音频对象零警告，checkpatch/diff check、完整构建、770模块兼容、FAT精确回读/fsck通过。完整构建只有未改EUD的既有unused-function警告；两个模块差异仅build-id。Image SHA256 `66dc177113d1b137a2089f5c1173bd5c71d527b522757304b5918e505bd14b0e`，logdump `6e3ebbe791455ae2c06a2374106f57c1d7ea0aac358191c44d8322b8d50f16cb`。初始source/build JSON里的pending/deployed=false是当时状态；实际部署由[新启动与分区回读](runtime-validation.json)证明。

切换前从175新取身份、完成音频/显示/NGD停机，临时关闭当前启动fbdev emulation，DRM关闭fd后复核inactive。只发送一次F1，一次logdump刷写；boot172、persist/NV不改。新启动uname-v为`#176 SMP PREEMPT Wed Oct 14 17:43:39 CST 2026`，boot/logdump/persist哈希、SD1和GPIO137/138/140、WCD版本及声卡通过。首启MBHC/jack各一次，无machine手工重新绑定。

## 实机回归

[10次重绑定](reprobe-validation.json)为codec两次、MFD父设备硬复位八次，每次恢复唯一声卡、Pulse card及HiFi (Mic, Speaker)，并录入48000帧。旧regmap目录消失，18个已打开旧debugfs句柄均返回EIO，新name可读，MCLK删除再创建，没有Oops。父设备卸载时五路供电consumer消失，绑定后各为1；codec单独卸载保持父设备供电，每次均配平。没有手工重新绑定machine，也没有额外恢复bind。

[录音启停/暂停](capture-stop-validation.json)通过八次FE16/32/48kHz录音、三次同PCM真实PAUSED/RUNNING恢复，后端固定48kHz，trigger返回全0，WCD underflow/overflow/Port Closed新增0。

[原生四例](dmic0-ucm176-low24-analysis.json)使用-24dBFS的997/1511Hz编码音、DMIC0及目标功放关闭负对照。左右相关0.9292/0.9952，开启与关闭功放的频带差19.48/41.23dB，左右均检出、采样无削顶。[桌面双向测试](desktop-acoustic-validation.json)使用普通用户paplay和parecord，左右相关0.9331/0.9727，对同启动关闭参考差18.38/40.23dB，sink/source volume与mute保持。这个编码和功放对照能区别环境风扇声；没有把测试音检测当成日常音乐音质验收，也没有把171人工听音挪作176人工证据。

[最终收据](final-validation.json)955.71秒、taint0：所列WARN/Oops/ASoC/NGD中断、读超时、bring-up、MCLK和端口错误计数均0；MBHC/jack各11次对应首启及10次有意重绑。PCM关闭，两功放68/68配平、关闭静音，17控件恢复，单Pulse CARD/alsa-card与HiFi profile，五路consumer各1，NGD suspended；NV/persist、模块132与UCM173核验通过。与175那次真实NACK分属不同启动，历史没有被清零。[汇总](checkpoint-validation.json)通过本轮规定回归，约16分钟收据不等于长期稳定。

## 证据与续作

私人包在`E:/edk2-samurai-out/kernel176/k176-all-private.tar.gz`与两个声学包；手机`/var/lib/samurai/k176*`保留身份、原始日志、阶段和录音。公开目录只保存代码及脱敏报告。回归脚本首次准备的字符串替换曾产生SyntaxError，链条在上传/执行前停止；修正后只执行这套10例一次，不能写成驱动失败后重跑通过。

WSL内核树tracked现在10文件：新增core及两份SLIM header，MFD176，machine/codec175、公共MBHC/DTS172、NGD/messaging168。15个显示源163保持；EDK2 BDS源码164、生成Build固件172、FdtBlob旧129及Mesa149保持。

用户暂无耳机，不重复询问；有实物后再验3/4段、插拔自动profile、声道、耳麦/按钮。接着验证系统休眠/SSR、正常启动/冷启动和长期恢复，再补音质、瞬态与扬声器保护。callaudiod拥有端口选择，不为缺少module-switch-on-port-available强制补载。回退保留logdump175及完整boot172/logdump172+UCM173；175本身有已知复位超时，不将回退称为完全验收版。继续前读[检查点](../../NEXT-SESSION.md)和[操作边界](../../WORKING-BOUNDARIES.md)，再次切换须取当前身份。
