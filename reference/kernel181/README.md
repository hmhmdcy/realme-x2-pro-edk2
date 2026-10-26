# 181：离线 IRQ 清理修复与 ADSP 停启、左右声学验证

2026-10-14。内核181已部署，保留180的PDR事务/世代/寿命和同步停止parent IRQ修复；新增已离线时的软件IRQ清理。初启动及一次实际ADSP停启通过，恢复后的原生/桌面左右编码音检出。完整音频goal active，实物耳机、自动crash恢复、更长PM/跨启动及音质/保护尚未完成。

## 离线清理的真实语义

180停启已经消除PDR超时、IRQ读洪流与ASoC错误，但释放六个virtual IRQ仍向已断开的SLIMbus写config/mask，产生72/6错误。[小补丁](offline-irq-cleanup.patch)在同步停止parent IRQ后，仅当sdev状态为DOWN，将现有main MAPLE regmap设为cache-only，再清理children和IRQ域、销毁map。缓存从不同步或重放；新UP重新建立map、硬件初始化和IRQ。普通UP状态驱动移除仍执行真实I/O，interface的无缓存策略未改变。

这是显式的软件资源清理模式，没有模拟寄存器读值或宣称硬件已接受写操作。实际`regcache_cache_only`、`_regmap_write/read`和MFD函数验证：离线硬件访问次数0；缓存外读取返回EBUSY且值不改，非法写错误保留；在线清理仍访问硬件，20次DOWN/UP中重建的新map为正常模式。[91场景与11负对照](host-tests-validation.json)。PDR27场景/六负对照沿用180已验证的相同源码哈希，合计当前改动覆盖118场景/17负对照。两个阶段的host传输/工作队列仍为薄适配，不代替实机验证。

[构建](build-package-validation.json)W=1对象无警告、checkpatch通过；完整编译/FAT回读与770模块兼容通过，仅两个既有模块build-id差异，保留runtime模块132。PDR源9bed7403…不变，MFD源5c4469fb…；其它九音频源和15显示源163保持，DTB/boot172、UCM173、Mesa149保持。

## 部署与恢复

从实际180新取身份，停止桌面/无线/remoteproc、验证CRTC inactive和供电/功放/PCM，私人包全部取回后冻结。使用已验证的Linux RESTART2路径；本次停机/冻结前置JSON已捕获，EUD关闭后SSH reset作为连接边界，随后新查目标fastboot/产品/分区大小，只刷logdump181。回退logdump180完整保留，其自身有72/6已知错误，不宣称全恢复正常。[初启动](runtime-validation.json)48.76秒#181、taint0、card/桌面自动恢复，所列PDR/IRQ/ASoC/DMA等故障0，分区/NV通过。

[一次受控停启](adsp-restart-validation.json)确认实际offline、card/两regmap/一MCLK移除、五consumer释放，两旧name FD均EIO；start后自动恢复HiFi(Mic,Speaker)、资源和录音，无machine手工重绑。PDR listener、IRQ读/config/mask、ASoC、DMA、FIFO、QMI等待等本轮所列故障均0，测试通过。仅证明这一次受控恢复，不扩大成真实自动crash/所有SSR已验收。

## 恢复后声学与最终现场

[原生四例](dmic0-ucm181-low24-analysis.json)左右相关0.9574/0.9327，对应功放关闭参考差19.99/43.03dB；[用户会话paplay+parecord](desktop-acoustic-validation.json)相关0.9575/0.9942、差20.17/41.89dB。两声道均检出、无削顶，gain不改，mixer及sink/source volume/mute恢复。桌面引用同boot原生amp-off参考，不声称另做桌面独立amp-off实验；171人工双组滴声仍有效，本轮不是人工音乐音质验收。

[最终892.99秒](final-validation.json)同boot、taint0、ADSP running，单card/alsa-card和HiFi，PCM关闭、双功放13/13配平静音、16个被保存控件恢复，五consumer各1、两map/一MCLK，live main cache-only=N、NGD suspended。当前ring从0秒开始且保留#181启动banner，所列20项故障全boot均0；不扩大成未列出的系统问题全清。NV/persist/boot/logdump及770模块132核验通过。历史178/180失败保留，181通过不覆盖它们。

私人镜像/日志/身份/录音在`E:/edk2-samurai-out/kernel181/`与手机`/var/lib/samurai/k181*`。logdump181哈希`56aa1c463d118f9de8d5dbd2cad3dc6b2ab1ff9f36d4027c77d457520b702a55`，Image`ae0eb8e0de80540cfe4349870020c1370534975bc30d90190c59afdf1d6afd11`；boot172哈希77e1a272…保持。下一步做活跃流/自动crash恢复和更长PM、跨启动、音质/保护；用户暂无耳机，不重复问。当前摘要与回退见[检查点](../../NEXT-SESSION.md)。
