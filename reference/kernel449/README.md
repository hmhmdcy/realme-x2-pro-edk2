# 449：用户身份、同一 Manager 循环与五分钟取流；发现旧统计重复回执

2026-10-23。复用448核心、441 build4三模块和443主摄原厂mode4配置，未改算法、调校或正式安装。实际应用以uid10000、CapEff=0运行，分别验证原生和隔离IPA下同一CameraManager／Camera／线程720p→1080p→720p的三个开停流周期。

六周期共263张成功图像（247 math＋16 bootstrap）、265次物理IPE完成；各epoch独立，同SOF PD10、实际GTM cookie／generation、WB上下文和成功历史通过，每次停流在Manager仍存活时读回原CPU掩码。[生命周期审计](lifecycle-validation.json)通过。

## 持续消费者及失败

初次长用例误用了363固定50秒fixture，1405张后被SIGINT终止；这不是相机崩溃，也不作为长测通过。4个IPA孤儿代理已通过精确任务路径／uid／PPid和pidfd核对后SIGTERM退出，无SIGKILL。[清理](orphan-cleanup-validation.json)。原事务r1结束，不重放。

修正仅限探针：新增单调时钟、有上限的fixture超时，默认仍50秒；GStreamer探针收到INT／TERM后执行GST_STATE_NULL清理。实际ARM64构建及8个fixture参数边界通过。[构建](long-client-build-validation.json)、[边界](fixture-guard-validation.json)。新r2仅执行取消和长期两项，没有重跑已通过的生命周期用例。

| r2消费者 | 成功图像 | math／bootstrap | 结果 |
| --- | ---: | ---: | --- |
| 隔离1080p，6秒fixture主动取消 | 88 | 85／3 | 子进程正常exit9，停止／亲和恢复完成，无代理残留 |
| 隔离1080p，9000帧 | 9000 | 8997／3 | 正常exit0；PTS覆盖300.509秒、29.946fps，33个单SOF缺口，最大PTS间隔66.546ms |

9000个成功图像的同SOF PD10、GTM、WB及实际IPE成功历史匹配。但严格原始回执审计发现5个已失败旧统计token再次回执，第二次返回-ENOENT；因此[硬件审计](hardware-validation.json)总体`passed=false`。诊断审计只单独排除这5条已明确识别的负回执，保留原始严格失败，不把完整事务写成通过。后续[450](../kernel450/README.md)针对这一底层缺陷修复。

源码中statsProcessed淘汰旧统计时先同步调用IPA，随后才删除本地map／deque记录。同步隔离调用等待期间能够重入统计回调，形成重复消费；宿主真实源码片段随后在450重现了重复回执及额外删除下一条记录。33处SOF缺口的根因仍待独立定位，不据此宣称旧441积压已关闭。

r2驱动最终计数9088 jobs／completed／direct_completed一致，failed／cancelled／first_error均0。内核日志只保留后9000次完成，环形日志不覆盖整个事务；不能声称9088条内核日志逐一核对。观察器取得105个长期样本，camera-thermal约35.3→41.9℃、最大42.3℃，读取各温区耗时使实际间隔不恒为1秒；这不是功耗或完整热验收。

## 恢复与边界

[r2事务](runtime-r2-validation.json)正常结束；[恢复](current-state-validation.json)、[残留](residual-r2-validation.json)通过：正式440 r32／r27与434模块、epoch0、资源释放、四设备suspended、P/W各一个uid10000、taint0，无新增内核故障或代理／观察器／临时用户目录残留。永久充电manifest34d46f4c、三模块、900／250mA限流和native100mA额度保持；同a30 boot／k449 guard。手机／SDK已交还充电侧，下一轮需重新协调窗口。

LTM独立因果证据继续引用[442](../kernel442/README.md)：同FULL／参数仅更换真实／黑／白／真实PD10改变输出，真实重复等于实拍。449不重复扰动回放，原厂数据不变。编码录像、无丢帧30fps、完整时延／功耗／热、其它镜头／AF／模式／光学／多摄仍未验收。照片、完整日志与二进制只存私有kernel449和手机事务目录；不发布、不永久安装。
