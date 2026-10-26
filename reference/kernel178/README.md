# 178：相关机型复查与 ADSP 重启断链错误

2026-10-14。本轮仍运行kernel176/logdump176、boot/DTB172、UCM173，没有修改、构建或刷写新内核。用户再次询问相关机型的Linux音频移植做法，已复查OnePlus 7T Pro实际源码和验收记录；随后一次受控ADSP停启暴露PDR超时、断链寄存器访问及IRQ错误洪流。声卡自动恢复、两旧debugfs句柄EIO、资源回收有证据，但本轮重启测试未通过。失败后原生/桌面左右声学复测通过，主通路当前可用；完整音频goal active。

## 相关机型实际采用的方法

再次用git ls-remote核对[hotdog移植仓库](https://github.com/Sr-0w/hotdog-linux-bringup)，HEAD仍为171已固定的`47087509c4289c2580c54f5433e55366b2e00445`；[重新获取的来源/哈希](related-model-provenance.json)保存了状态表、WCD与扬声器记录和实际0039补丁，外部脚本未执行。

- [OnePlus扬声器记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/evidence/2026-08-05-mainline616-internal-speakers.md)按原厂mixer/profile确认MI2S格式和功放slot，先验证时钟，再开放功放；加入UCM后，用麦克风测左右输出和桌面软件音量衰减。该机使用TFA9874与S24/32-bit slot，不能把这套功放寄存器、字宽或增益直接当作本机MAX98937的配置。
- [WCD传输记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/evidence/2026-08-05-mainline616-wcd9340.md)先隔离SLIMbus/MFD/codec注册，再建立machine card和声学路由，没有以设备注册替代出声证据。[当前状态](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/status.md)仍把音频列为Partial，耳机、部分麦克风及保护等开放，不是一套已完成所有功能的通用补丁。
- 本机[171核验](../kernel171/README.md)已将Realme原厂19781 overlay/pinctrl和OnePlus0039补丁独立对照：SD1/GPIO140线索实际进入本机修复，改后左右出声且用户确认双组滴声。Realme GPL的掩码2和主线sd-lines数组索引1语义有区别；原厂来源固定`9668fcdc6ec15be7a10d66f7b93c347829e0fdb6`。本机UCM、DMIC路由和2700mV偏置按本机证据保持，没有套用OnePlus AMIC配置。

本轮检索与核验得到这些可用参考，没有据此声称发现另一套完整Realme X2 Pro原生音频方案。参考结果与本机验证分别记录。

## 受控停启的结果和真实失败

依据[remoteproc接口](https://docs.kernel.org/staging/remoteproc.html)与本树源码核对stop/start。stop可能只减power引用，所以本轮同时检查实际offline；正常停启经过qcom_common的SSR通知链。NGD中相关tx_lock/ctrl锁顺序又对照了[上游讨论](https://lists.openwall.net/linux-kernel/2026/03/31/2370)：本机168已将tx_lock限制在DMA退出阶段，没有把child absent通知包在tx_lock内。运行态与SSR其它并发仍需验证，不把这段讨论当成全套恢复完成。

[一次停启](adsp-restart-validation.json)确认ADSP实际offline、声卡/两个regmap/MCLK移除、五路consumer释放，两旧name句柄均EIO；start后card与HiFi(Mic,Speaker)自动恢复，能够录音。没有重复stop/start、整机重启或machine手工重新绑定。MPSS仍running、SLPI仍offline。

[失败审计](restart-failure-audit.json)原始窗口中有IRQ状态读-107共26510、IRQ config写失败72、mask同步失败6、ASoC错误6、PDR注册监听超时1。不能只引用声卡恢复和录音返回0来写SSR通过。4749.055秒ADSP停完、4749.264重新up、4749.442 SLIM注册；4752起新录音触发成功，4754.351 PDR listener等待-110，4754.484新stream STOP返回-107并有ASoC错误。原始日志在私人包保留，重复日志曾使kernel ring覆盖旧内容；当前dmesg中错误少于原始计数不代表故障被修复。

[合并已保存时间戳行](known-failure-history.json)又确认了稍后4759.979秒的一次PDR超时及额外IRQ/清理错误；扣除停启前基线后，已捕获的下界是IRQ读27720、config144、mask12、ASoC6、PDR超时2。原窗口收据不替换。停启前保存的kernel176初启动日志另有PDR超时3、config8/mask1，先前176/177的所列故障项没有覆盖这些；不应将旧“所列故障0”扩大成启动的完整日志干净。现需一起核对启动和重启的PDR/IRQ路径。

## 定位线索与未完成的修复

[源码快照](source-validation.json)确认内核10个改动文件仍与176一致，MFD/codec/PDR/QMI helpers均为builtin。当前有两条需要直接验证、修复的线索：

1. MFD DOWN先移除children，随后才删regmap IRQ chip。总线已断开时，parent level IRQ仍可进入线程读寄存器；child IRQ退出又尝试同步mask/config。需要在移除children前正确停止parent IRQ，并设计已离线时的硬件访问与软件资源释放，不能只降低日志等级或跳过真实错误。
2. `pdr_notifier_work`持有list_lock调用register_listener，并等待QMI最多5秒；同一handle的服务器新增/删除回调也要list_lock，QMI接收worker串行处理control和reply。这存在阻塞接收/更新服务器状态的可能，注册失败又直接向客户端发DOWN；与新声卡恢复后出现超时/断链的时序吻合。实际阻塞栈/具体旧世代回调仍未直接测量，待用实际函数并发重现验证。修复需考虑释放锁等待、事务地址/结果快照和服务器/通知世代；不能加sleep掩盖、忽略所有PDR DOWN或仅让日志好看。

尚未实施新内核补丁、并发host验证或新构建。`test-adsp-restart.py`未计入最初的IRQ/config/mask故障，所以单独补完整失败审计；原始测试本身也已因6个ASoC错误断言失败，没有绿色验收。后续测试需纳入这些故障项并记录操作时间/阶段。

## 失败后当前功能验证

[原生四例](dmic0-ucm178-low24-analysis.json)左右编码相关0.9124/0.9873，[桌面paplay+parecord](desktop-acoustic-validation.json)相关0.9553/0.9915，两声道均通过目标功放关闭参考；采样无削顶、路由及volume/mute恢复。这证明目前仍能出声、拾音，不抵消已记录的重启失败，也不算日常音质验收。

[最终6172.11秒](final-validation.json)同boot、taint0、ADSP running、单CARD/alsa-card与HiFi(Mic,Speaker)，PCM关闭、功放85/85配平静音，17控件恢复、五路consumer各1、两个regmap/一个MCLK、NGD suspended；NV/persist/boot/logdump/770模块132核验。只在失败后新声学窗口中，所列ASoC/IRQ/PDR及其它音频故障为0；用窗口起点仍在ring中的时间戳核对，明确保留原始失败计数，不能写本boot所有错误0。[汇总](checkpoint-validation.json)明确controlled_adsp_restart_passed=false。

私人证据在`E:/edk2-samurai-out/kernel178/k178-failed-restart-private.tar.gz`、`k178-all-private.tar.gz`和两个声学包，手机`/var/lib/samurai/k178*`。用户暂无耳机，不重复问；下一步优先并发重现与PDR/IRQ断链修复，再验证受控重启/真实自动crash恢复、较长PM、跨启动和音质。当前部署/回退见[176](../kernel176/README.md)和[检查点](../../NEXT-SESSION.md)，边界见[WORKING-BOUNDARIES](../../WORKING-BOUNDARIES.md)。
