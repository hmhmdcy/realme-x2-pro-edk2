# 448：开停流管理线程容量租约，首个焦点采样已使用选定CPU

2026-10-23。将[447](../kernel447/README.md)临时亲和对照接入相机生命周期：[0060](0060-camss-stream-thread-capacity-lease.patch)只新增[租约helper](thread_capacity.h)及管线开停流调用，开流前按实际允许CPU的容量选择，停流／启动失败时恢复。宿主ASAN／UBSAN与实际ARM64各21案例通过，另以uid65534、有效capabilities=0执行实际亲和设置／恢复通过。

本轮766张自动处理图像＝750 math＋16 bootstrap，另双流6IPE，总772物理完成；RAW-only6无IPE。720p／1080p各普通／隔离120帧均约30.056fps、所有消费样本无SOF跳号；首次焦点采样约3.21—3.27ms，所有活动路径停流后读回原CPU掩码。主摄实际AF Focused，23次镜头写入成功。**候选未永久安装，持续录像、功耗／温度与同一Manager反复开停流仍待验收，旧441积压根因未宣称关闭。**

## 生命周期与降级

只对实际活动焦点路径获取租约，从`sched_getaffinity`当前允许集合读取`cpu_capacity`，保留其中高于最小容量组的CPU；同容量或缺失容量信息时不调整。不固定CPU编号、不提高频率或调度优先级，不修改温控。当前本机实际选择4—7源于容量294／837／1024，并非生产代码硬编码。既有允许集合仍是上界。

同一CameraManager线程的租约引用计数，最后一个持有者恢复；外部更改亲和后保留外部策略。正常pthread退出的TLS守卫标记所有者消失，跨线程释放与退出共用互斥锁，避免针对已复用TID操作。恢复错误保留租约供重试；最后对象销毁仍失败则保存待恢复状态，后续获取先重试。读取／设置失败不改变图像算法或使采集失败；无法执行恢复的情况有明确返回状态，不能冒充已恢复。本轮实机各活动路径均为`reason=restored`且读回成功。

获取点位于首次采集streamOn之前，所有启动error路径调用stopDevice；释放在队列、IPA、镜头停止之后、焦点网格释放之前。没有改IPA6、FoM、AF状态机、DMA同步、原厂调校、441 build4模块或请求所有权检查。[源码验证](source-validation.json)、[重入验证](reentry-validation.json)。

[租约验证](capacity-validation.json)从真实生产头编译，覆盖动态且非4—7的CPU编号、共享／幂等、受限集合、容量缺失、读／设置／读回／恢复失败及重试、外部策略、cpuset交集、所有者退出／重用、跨线程释放和实际系统调用恢复。21案例通过宿主ASAN／UBSAN及实际ARM64；[无特权验证](unprivileged-validation.json)在宿主uid65534、CapEff=0下复用该二进制，证明自有线程不依赖root或CAP_SYS_NICE，不冒认为本轮手机root探针已用用户身份运行。

核心增量构建122.65秒，SHA `72d2aac0…`；IPA `4c90047d…`、签名及proxy与444完全一致，主摄仍443原厂mode4配置、前摄仍440原厂配置。[构建](build-validation.json)、[载荷](runtime-inputs-validation.json)。无需重建内核或假定现有uclamp支持。

## 实机审计

测试移除了外部亲和注入，使用正常Camera API。每帧仍核对同SOF PD10、实际GTM cookie／generation、WB版本、来源统计、IPE入队及最终成功历史；取消不提交成功历史。[完整审计](hardware-validation.json)、[终态事务](runtime-r1-validation.json)。

| 路径 | 成功图像 | 首次采样wall | 全段采样最大 | PTS fps／稳态跳SOF |
| --- | ---: | ---: | ---: | ---: |
| 720p普通 | 120 | 3.213ms | 3.281ms | 30.056／0 |
| 720p隔离 | 120 | 3.273ms | 5.032ms | 30.056／0 |
| 1080p普通 | 120 | 3.239ms | 7.550ms | 30.056／0 |
| 1080p隔离 | 120 | 3.272ms | 6.784ms | 30.056／0 |
| 前摄2304×1728→640×480隔离 | 44 | 无活动焦点路径 | 无租约 | 自动版本／成功历史通过 |
| 主摄4608×3456→640×480实际AF | 242 | 2.270ms | 3.429ms | Focused，23镜头写入 |

主摄RAW-only6与双流6也从首个焦点采样使用选定CPU并在停止时恢复；RAW-only保持无PD10／tone／IPE，双流6次成功历史。前摄没有获取租约，stop报告inactive。活动路径共7组，均在Manager线程退出之前恢复原掩码；包括首个采样的所有CPU端点都位于动态选定集合。物理完成计数与内核日志772一致，无新内核故障。

相较447在首图之后调整的隔离对照，720p／1080p首次采样wall由22.755／67.860ms变为3.273／3.272ms；跨启动及充电环境未受控，不将全部差异归因于本改动，也不把焦点采样当请求到首图的完整延迟。[有界比较](comparison-validation.json)、[时延](latency-validation.json)。独立LTM消费因果证明仍沿用[442](../kernel442/README.md)，本轮未重新扰动PD10回放。

## 新启动、恢复和续作

充电侧已完成单属性DT-only boot切换，新实际boot为a30fb444…ec280，原密钥不变。本轮采用独立448 guard重新核对正式440／434；旧446／447 guard已过期。新基线包含常驻samurai-charging及三模块、900mA输入／250mA充电上限、原生UDC预算100mA／源CDP预算1.5A，未卸载或修改它们。前后模块note、限值、预算及开机启用一致。[前置](preflight-validation.json)、[恢复](current-state-validation.json)。

相机结束恢复正式440 r32／r27、434三模块和原厂配置，epoch0、taint0，ICP／CAMSS／双CCI suspended，P/W各一个uid10000；相机事务未刷写或重启。手机／SDK已明确交还充电侧做两模块PM依赖增量及单次RTC／s2idle，交还前仅离线；该窗口结束后的新充电note必须重新采用，不能沿用本轮旧快照。

下一步验证同一Manager反复开停流、用户消费者及必要的失败／外部策略场景，再做持续录像和功耗／热条件；不能仅凭短样本发布。多租约／失败路径本轮来自真实helper测试和源码错误流检查，没有在手机故意制造streamOn失败或宣称物理多摄并发已适配。其余镜头／实际AF、其它尺寸／消费者、legacy／manual／v2／HDR、光学、连续AF／距离、第五2MP和多摄几何／同步继续按[完整范围](../kernel363/REMAINING-CAMERA-SCOPE.md)推进，原厂数据优先。

448 r1终态勿重放。317项收集文件、照片、日志及二进制只在私有kernel448及手机事务目录。WSL源码／build仍先调用284挂载守卫；不格式化、不改锁、不卸共享卷；SDK bind串行，按文件脱敏同步，不push。
