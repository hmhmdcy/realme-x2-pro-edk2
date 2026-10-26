# 175：jack、regmap、MCLK 生命周期修复与父设备复位超时

2026-10-14。已部署 kernel175 V4/logdump175，保留 boot172、DTB172、modules/software132、Mesa149、UCM173。首启 codec 两次初始化后声卡自动恢复，不再需要174的 machine 手工重绑；两个 codec 重绑定和一个 MFD 父设备重绑定通过。第二次父设备绑定发生 NACK/读超时，后来又探测成功，可靠性仍未闭环。之后录音启停、真实暂停/恢复、原生四例和普通用户桌面双向音频回归通过。完整goal保持active。

## 源码与构建

[增量补丁](card-and-wcd-lifetime.patch)修改三文件：

- machine在link exit解除RX/TX共享jack，时点在codec component移除之前；card probe/remove复位jack_created/component。实际ASoC核心只有card进入probed生命周期才执行remove，因此新增probe入口也覆盖BE初始化失败的清理，不能仅靠晚期remove标记。
- MFD为UP/DOWN/remove建立私有互斥状态，重复通知不重复分配；子设备先移除，IRQ domain随后注销，最后regmap_exit；初始化失败逆序清理。保持原有上电值，检查所有bring-up写错误，regulator get改为devm。probe结束处理已为UP的bus device，并在尚无私有数据的早期通知返回defer，避免初始UP状态被SLIM核心的“状态未变”过滤掉。
- codec的interface regmap改由codec设备负责释放，解除映射后再归还sidev引用；logical address获取错误向上传递。嵌入codec私有内存的MCLK hw也改为codec所有，provider和hw一起回收，注册错误不再忽略。

[函数级验证](host-tests-validation.json)共73场景：machine27（含25轮重新绑定及实际ASoC probe/remove函数）、MFD36（13个失败点、20轮16线程UP/DOWN、初始UP与早期通知）、interface6、clock4。ASan/UBSan、7个故意删掉清理/入口或用错误owner的负对照通过。MFD部分添加失败按本树mfd-core回滚契约建模；这些host结果不能替代真实probe、PM和复位时序。

[V4构建](build-package-validation.json)的W=1三个改动对象零警告，checkpatch/diff check通过，完整构建只保留未改EUD的unused-function警告；770模块与132兼容，仅两个build-id不同。配置、DTB172、15个显示源保持，NGD/messaging仍168，174端口IRQ补丁保持。FAT精确回读/检查通过，只刷logdump，boot/NV回读一致。

Image V4 SHA256 `250c435567d1ed25150715b317d9ff0c498c515c84727ffde64b3680a429e5c2`，logdump V4 `cbeedef03586aae616f8c7ec9423f5667904682fa128c184b5c0b7620392acb2`。同一175的几个未部署候选原件都保留，uname-v时间沿用第一次构建，不能靠banner区分V1—V4；实际部署以分区哈希证明。首轮模板误留modules-root174，被已有目录保护拦下，未改旧模块；[失败记录](first-build-rejected.json)保留。V2增加clock owner，V3增加card probe失败清理，V4增加初始UP处理；只有V4部署。

## 实机结果及失败范围

[首启](runtime-validation.json)79.77秒：WCD/MBHC与jack绑定两次，但声卡、Phosh/Pulse自动可用，ASoC错误/WARN/Oops为0；无machine手工重绑。两份当前regmap name读取正常，boot172/logdump V4/NV通过、SD1/GPIO140保持。

[重新绑定](reprobe-validation.json)已完成的V2三例是codec两次、MFD父设备一次。每例移除对应regmap目录和mclk，旧文件句柄返回EIO，新绑定自动恢复声卡、单Pulse CARD/profile、两个regmap与一个mclk；每例再捕获48000帧。总计4个旧句柄有持久收据，读新name无Oops。此前V1第一例在恢复成功后仅等待3秒检查PCM idle，早于Pulse默认5秒，测试判据失败；后续按实际PCM关闭等待至12秒。不能把这次计时判据误判为驱动故障。

V2第四例（第二次父设备绑定）未完成：237.714秒NGD错误中断`0x82000000`，即TX_NACKED_2加TX_MSG_SENT；237.998秒MC0x60/LA0xcf读请求返回-110，WCDbring-up/probe失败。238.049秒起又有chip ID/codec/MBHC成功探测，最终声卡恢复。测试phase仍为unbound，未记录finally里的restoration-bind；因此只报告“失败之后又探测成功、当前已绑定”，不将其说成测试重试通过。原始失败日志与阶段文件保留。

这个失败有明确I/O证据，下一步核对硬复位后main/sidev logical-address缓存与物理枚举时序，不靠额外sleep或重复bind掩盖。当前MFD会拉低reset，但初始UP路径可直接读沿用的逻辑地址；这是调查线索，尚未证明因果。另需补查SLIM bus wrapper在MFD probe已返回后get_laddr失败时的enabled regulator清理，devm get引用管理不等于enable自动清理。内部slim_report_absent实现可失效地址，公开头文件尚无该声明；先按API/锁和回调顺序设计，不直接无锁改缓存字段。

[停止/暂停](capture-stop-validation.json)在超时恢复后通过8次FE16/32/48kHz录音及3次同PCM真实PAUSED/RUNNING转换，后端固定48kHz；trigger全0，WCD underflow/overflow/Port Closed新增0、mixer保持。

[原生四例](dmic0-ucm175-low24-analysis.json)左右相关0.9776/0.9983，功放关闭对照差19.53/43.25dB；[用户paplay+parecord](desktop-acoustic-validation.json)左右相关0.9389/0.9546，对同启动原生关闭参考差18.49/42.24dB，sink/source volume和mute保持，均检出编码音。

[最终](final-validation.json)1115.14秒、taint0，ASoC/WARN/Oops/MCLK/WCD端口错误0，保留上述一次NGD错误中断/读超时/bring-up超时；不能写“所有错误为0”。单CARD/alsa-card、HiFi (Mic, Speaker)，真实jack off，PCM关闭，功放37/37配平关闭静音，17控件恢复，NGD suspended，NV/persist/模块132及UCM173核验通过，MBHC/jack总计7次对应多次绑定。callaudiod继续拥有端口策略。

175通过了原172 debugfs name的当前读取和已删除文件句柄路径；修复了缺失的资源清理，但未用无限压力证明所有debugfs或SSR缺陷都消失。父设备复位/冷启动/SSR/休眠/长稳、正常音质/瞬态仍开放；用户暂无耳机，实际插拔、3/4段、耳机/耳麦/按键未验，不重复问。171的人工听音不移作175音质证据。

## 产物与续作

完整私人证据在`E:/edk2-samurai-out/kernel175/k175-all-private.tar.gz`和两个声学包，手机`/var/lib/samurai/k175*`保留初次测试判据失败、V2父设备失败及恢复。公开目录含脱敏验证、补丁和脚本。WSL内核树tracked现在7文件，多了MFD；[源码哈希](source-validation.json)与V4一致，尚未开始176修改。

回退可用完整boot172/logdump172+UCM173；boot174/logdump174候选与171人工出声SD1版本也保留。切换前重新核对当前启动和完整停机，旧175 preflash是174身份；一次F1后USB EIO不重复发。工作规则见[边界](../../WORKING-BOUNDARIES.md)，当前检查点见[NEXT-SESSION](../../NEXT-SESSION.md)。
