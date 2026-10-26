# 179：相关机型复核与 PDR 接收锁阻塞重现

2026-10-14。用户再次询问相关机型的 Linux 音频移植处理。本轮核对171/178的来源和当前部署，并用实际内核函数重现PDR/QMI锁阻塞。没有修改内核源码、构建Image、刷写或再次重启ADSP。手机仍运行内核176，完整音频goal active。

## 相关机型给出的可用参考

- [Realme官方19781音频overlay](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/19781/sm8150-oppo-audio-overlay.dtsi)与pinctrl提供本机的线路/偏置依据。[OnePlus 7T Pro实际0039补丁](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0039-asoc-hotdog-enable-bounded-tfa9874-speaker-output.patch)独立采用Quaternary RX SD1/GPIO140。171已把这一线路修正用于本机；随后左右编码音通过，用户明确确认两组滴声来自手机。
- [OnePlus扬声器记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/evidence/2026-08-05-mainline616-internal-speakers.md)先验证MI2S格式/slot/时钟，再加入UCM，并用麦克风区分左右声学输出、验证桌面软件音量。该方法已用于本机；TFA9874的寄存器、字宽和增益没有套到MAX98937。
- 新搜索还取得[OnePlus 6/6T WCD9340 MBHC阈值补丁（2026-09-22）](https://lists.openwall.net/linux-kernel/2026/09/22/2906)。作者按原厂下游校准设置耳机/按钮检测阈值，这支持从本机校准取值的方法；它属于另一机型的提案，不是本机已验证的数值，也没有在本轮应用。本机172偏置和MBHC修复、173耳机路由仍需实物耳机验收，用户目前没有耳机。

来源固定提交和哈希仍见[171](../kernel171/README.md)、[178来源复核](../kernel178/related-model-provenance.json)。本轮没有找到可核验的、覆盖本机完整音频功能及恢复的现成补丁；不能把这一有限检索结论扩大成全网不存在。

## 实际函数并发重现

[测试脚本](test-pdr-rx-lock.py)从当前内核提取四个PDR函数及`qmi_data_ready_work`、`qmi_txn_wait/cancel`，没有重写这些基线函数。pthread锁、列表、QMI消息和completion是薄适配；mock socket按顺序给实际QMI RX worker提供control通知和有效reply。测试等待缩短为200ms，内核实际等待为5秒，没有改变锁关系。

[七场景结果](pdr-rx-lock-validation.json)：

| 版本/消息顺序 | 实际结果 |
| --- | --- |
| 原函数，直接有效reply | 成功，客户端UP，无超时 |
| 原函数，无关服务DEL_SERVER后有效reply | RX阻塞在list_lock，注册超时并通知DOWN，晚到reply已无事务 |
| 原函数，无关服务NEW_SERVER后有效reply | 同样阻塞、超时、DOWN、丢弃晚到reply |
| 原函数，被跟踪服务DEL_SERVER后有效reply | 同样阻塞、超时；真实服务删除应产生DOWN，本例不把DOWN本身当作错误 |
| 仅锁外等待的因果对照，直接reply/无关DEL/无关NEW | 三例全部成功，无锁阻塞、超时或晚到reply |

gcc使用-Wall/-Wextra/-Werror及AddressSanitizer/UndefinedBehaviorSanitizer，最终编译与七例执行stderr均空。最初fixture因EI适配类型和缺少前置声明编译失败，修正适配后通过；未改生产函数。原函数的三个预期超时属于成功重现缺陷，不能写成三项手机恢复验收通过。

因此，持list_lock等待事务能够阻塞同handle的接收回调，哪怕control通知属于无关服务；这是可执行证据，不再仅是源码疑点。178实机4754/4759秒超时是否恰由这个消息顺序触发，仍没有实机栈/消息trace直接证明。因果对照缺少服务世代、对象寿命、locator/release和通知顺序处理，不能直接部署。

下一步需让事务等待和客户端回调退出list_lock，使用端点/结果快照，防止旧事务或旧peer通知覆盖新服务，并确保QMI回调及worker停止后再释放lookup/indication对象。同时修MFD移除children之前parent IRQ尚未停止的问题，再构建、验证初启动和ADSP恢复；不能加sleep、忽略所有DOWN或降低错误日志替代修复。

## 当前现场与证据范围

本轮只读实机核对：`uname -v`仍为#176，taint0、ADSP running、单Realme X2 Pro声卡，播放/录音PCM均closed。没有新增听音或声学测试；出声/拾音依据仍为171人工确认和178失败后原生/桌面左右复测。178保存的重启IRQ/config/mask/ASoC/PDR失败与初启动错误全部保留，没有因当前状态正常而清零。

生成C、可执行文件及日志位于私人`E:/edk2-samurai-out/kernel179/pdr-rx-lock/`。当前部署、回退和完整失败计数见[178](../kernel178/README.md)与[检查点](../../NEXT-SESSION.md)。
