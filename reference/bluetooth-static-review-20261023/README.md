# 蓝牙当前静态审查（2026-10-23）

**本页现为修复前历史快照。六类问题已完成[源码修复与离线验证](../bluetooth-static-fixes-20261023/README.md)，内核/radio以独立候选交付，尚未部署。** 下文行号、源码摘要和负对照属于修复前版本；当前测试脚本行号已有变化，不将旧报告冒认为新版本验证。

按用户最新要求停止蓝牙实际测试，仅审固定k363/r0、未部署PM r2、包采用逻辑及当前测试程序。确认两项高优先级退出问题和四类中优先级问题；下列为待修问题，没有改动受审源码、重建、安装或操作手机。它们不能直接解释本次漫步者“没有听到”。

## 已确认问题

| 优先级 | 位置 | 触发条件与后果 |
| --- | --- | --- |
| P1 | [hci_serdev.c:402](hci_serdev.c#L402)，发送访问在73–75行 | 注销先`hci_free_dev()`，404行才`cancel_work_sync(write_work)`。发送工作在写串口后被抢占、且没有额外引用延长hdev寿命时，可在释放后继续写`hdev->stat`，产生UAF。HCI core注销不取消该UART工作。当前r0已有，r2只改qca_suspend，未覆盖。 |
| P1 | [phone-gatt-peer.py:606](../bluetooth-le-peer-20261023/phone-gatt-peer.py#L606) | `stopping=True`后608行直接写日志。磁盘满等写失败会在全部注销、断链、属性恢复、捕获关闭之前抛异常；再次stop及run的750行finally均因stopping跳过。GLib回调路径可能等到外层硬杀，Powered未恢复；独立运行也可能不退出。 |
| P2 | [hci_qca.c:546](../bluetooth-transport-20261023/source/hci_qca.c#L546)、[504](../bluetooth-transport-20261023/source/hci_qca.c#L504) | WAKE重传的GFP_ATOMIC分配失败直接break，跳过timer重挂，TX仍WAKING；没有在途ACK时等待队列停止前进，后续WAKING入队也不重启。idle SLEEP分配失败同样丢idle重试，保留AWAKE/TX vote直到后续活动。两者均r0已有/r2未覆盖；当前clock helper为空，不能推定物理UART时钟一直开启。 |
| P2 | [run-gatt-window.py:75](../bluetooth-20261023/run-gatt-window.py#L75)、[windows-gatt-central.cs:60](../bluetooth-windows-central-20261023/windows-gatt-central.cs#L60) | 主机接受整个私有输出根目录，Windows只接受专用central子目录。比如`bluetooth-20261023/gatt-r3`通过主机输出路径条件，却在手机已启动后被Windows拒绝。这次r3先因充电health拒绝，尚未实际触发路径错误。 |
| P2 | [usr_sbin_samurai-radio-address:35](../../linux-port/packages/samurai-platform/usr_sbin_samurai-radio-address#L35)、[49](../../linux-port/packages/samurai-platform/usr_sbin_samurai-radio-address#L49) | 缓存缺失时`load`以OR-list调用refresh，整段refresh不能依赖set-e。mktemp失败会留下空query，后续36/39行重定向指向根目录`/boot-id`和`/bt-query.log`或`/wlan-query.log`，随后DMS虽拒绝、helper虽退出，文件仍可能已创建。42–44行指针发布同样缺显式错误传播。应逐项检查创建/写入/发布成功；不涉及NV写入。 |
| P2 | [low-volume-speaker.py:160](../bluetooth-speaker-20261023/low-volume-speaker.py#L160)、[178](../bluetooth-speaker-20261023/low-volume-speaker.py#L178) | 解除静音后和播放期只检查音量上限，不验证sink.mute；PA随后静音时paplay/transport仍可能给出成功。成功记录也没有播放期mute读回。这是验收盲区；r4已有非零媒体，不能据此归因为本次静音。 |

serdev完整文件仅从固定提交`ba61a62293e0f6bc5838c06f2e85e033e3d702a8`复制，9454B、SHA256 `7ea43973798689b060eb9d7ca4359e87dcd8aa2b49f835cab4d5eb194c10b206`，不是读取另一个版本的工作树后推断。[引用释放链证据](kernel-source-evidence.json)包含hci_core的unregister/free和hci_sysfs release链；额外引用可能推迟释放，不能替代发送工作同步。

## 验证范围与处理顺序

[offline-recheck.py](offline-recheck.py)仅提取实际stop方法注入日志写失败、核对两端路径条件，并用最小dash程序确认OR-list/errexit行为；不导入蓝牙库、不运行WinRT/SSH/驱动。结果见[offline-validation.json](offline-validation.json)。内核竞态和OOM分支依据完整固定函数及调用链静态核对，未伪称故障注入或硬件复现。

先修serdev工作停止与hdev释放顺序、GATT无条件清理；再补IBS两条分配失败后的可恢复重试、统一输出路径及RAM缓存错误传播，最后补音频播放期静音/流身份读回。任何修正都须成为新候选，旧签名包及旧验证摘要保持历史含义，不能把现有PM r2称为全部异常路径已收敛。

包层目前仍有明确未验边界：[真实trigger输入对齐](../bluetooth-host-trigger-20261023/README.md)显示现场六索引、DB/world不同于旧363/115缓存，因此现场apply继续禁用；这是已知验收边界，不另外当成代码bug。新增[只读输入缓存工具](../bluetooth-host-input-cache-20261023/README.md)仅离线达到可审查状态，没有运行手机采集。GENI候选、BNEP/UHID最小配置及符号核对范围内，未确认其它静态缺陷。

充电会话报告R7已同Image正常启动、原key严格验证恢复且保护/正式相机配置通过，仍持图标复测窗口，随后交相机。本线未读取该新boot；用户已明确暂不做蓝牙实测，本线不排队、不连接音响、不增加音量。
