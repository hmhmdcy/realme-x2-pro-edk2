# 447：焦点长尾包含抢占等待，大核线程对照改善稳态

2026-10-23。本轮完成[446](../kernel446/README.md)留下的CPU／缺页／调度分辨。新增[0059诊断计时](0059-camss-focus-execution-observations.patch)，数值计算、工作区和IPA不变；两次终态事务共480张处理图像＝466 math＋14 bootstrap、480物理IPE，逐SOF／GTM／WB／成功历史审计通过。

无亲和限制的四个采样超过33ms帧均从CPU0开始，有非自愿切换，采样区间缺页均0；其中23—46ms未计入线程CPU时间。仅将CameraManager线程临时限制到容量更大的CPU4—7后，两路去掉前8帧的采样最大约3.48／3.41ms、约30.056fps，稳态跳SOF均0。**这是诊断对照，尚未接入正式流生命周期，没有认证首帧、持续录像、功耗或关闭旧441积压故障。**

## 实现与证据边界

在原采样函数前后读取`CLOCK_THREAD_CPUTIME_ID`、`getrusage(RUSAGE_THREAD)`及`sched_getcpu()`，记录wall／threadCPU、minor／major fault、主动／被动切换和两端CPU。只增加计时字段、快照与日志，原`LumaFocusWorkspace`／`measureLumaFocus`逐字节不变，FoM、AF状态机、原厂参数与DMA同步顺序不变；复用446精确数值证明，不重复无变化的大矩阵。[源码验证](source-validation.json)、[重入边界](reentry-validation.json)。

核心增量构建117.68秒成功，SHA `e03b4f4b…`。IPA `4c90047d…`、签名、proxy与444／446完全相同；443原厂mode4 profile、441 build4三模块和GStreamer探针不变。[构建](build-validation.json)、[输入](runtime-inputs-validation.json)。没有重新提取原厂系数、重建Image或修改硬件调校。

采样器只每约100ms读取策略报告频率，约500ms读取相关温度；自身CPU累计0.23—0.29秒／约15.4—15.6秒。报告频率不是硬件周期计数；wall减threadCPU包含观测开销、抢占／中断等等待，不可直接当纯调度时延。线程CPU也包含访存停顿及频率影响。fault计数只覆盖采样区间，不覆盖之前的mmap调用。读取实际vb2-dma-sg实现仍为页分配／`vm_map_pages`及标准DMA同步，未绕过一致性维护。

## 两个有界事务

两个事务都使用主摄4608×2592，720p／1080p隔离IPA，每路120帧。r1不改变亲和；r2从首个GST_IMAGE后，仅识别并调整输出FOCUS_EXECUTION的CameraManager线程，应用线程和IPA进程未改。实际CPU容量为0—3各294、4—6各837、7为1024；r2稳段两端CPU全部位于4—7，退出后目标线程不存在。没有修改系统频率、governor、温控或其它线程策略。

| 指标，去掉前8个消费样本 | 720p r1→r2 | 1080p r1→r2 |
| --- | ---: | ---: |
| 采样wall中位 | 3.385→1.984ms | 3.380→2.024ms |
| 采样threadCPU中位 | 3.363→1.973ms | 3.355→2.013ms |
| 采样wall最大 | 33.894→3.480ms | 21.543→3.406ms |
| 未计入threadCPU的差值最大 | 24.066→0.136ms | 10.563→0.030ms |
| PTS fps | 30.056→30.056 | 29.787→30.056 |
| 稳态跳SOF | 0→0 | 1→0 |

[r1逐帧审计](hardware-r1-validation.json)、[r2逐帧审计](hardware-r2-validation.json)、[比较](comparison-validation.json)。r1的720p SOF51／79／88采样wall约33.5—33.9ms、CPU约9.8—10.4ms；1080p SOF0约68.5ms、CPU约22.6ms，均有抢占且无采样缺页。r2的1080p首帧仍约67.9ms，发生在设置亲和前，不能声称启动长尾修复。两次顺序运行，照明、温度、其它调度未受控；只证明当前短样本的线程容量与抢占贡献，不把全部瓶颈归结于调度。

全部480物理完成与内核日志相符，成功历史只提交成功输出。原有同SOF PD10、实际GTM cookie／generation、WB版本、来源统计和停止取消检查保留；本轮未重复LTM扰动回放，独立因果证明继续沿用[442](../kernel442/README.md)。[r1事务](runtime-r1-validation.json)、[r2事务](runtime-r2-validation.json)。

## 恢复与下一步

447结束后恢复正式440 r32／r27核心、434三模块及原厂配置，epoch作业0、taint0、四设备suspended，P/W各一个uid10000，无新内核故障。[最终检查](current-state-validation.json)。r1／r2均终态勿重放，原件仅在私有kernel447与手机目录。相机未刷写／重启，SDK bind已卸载，窗口已明确交还充电会话；对方随后持久服务／DT切换中，不连接手机，等其明确交还并采用新启动后再测。

下一步把容量选择移到开流前，并在停流／启动失败时恢复，处理共享CameraManager线程、多用户、外部亲和变化、cgroup允许CPU及无能力／权限时的降级；不要把实验里的固定CPU4—7直接当生产实现。再覆盖普通／隔离、首帧及必要的RAW／双流／AF生命周期，随后验证录像与功耗。保留共享构建配置未启用UCLAMP_TASK，尚未重新查询运行内核配置，不能假设现内核支持uclamp；本轮未为此重建内核。[离线选项核对](scheduling-options-validation.json)。

446四摄／RAW／双流／主摄实际AF结果保留；其它模组镜头、其它尺寸／消费者、HDR／legacy／manual／v2、绝对光学、连续AF／距离、第五2MP及多摄几何／同步仍按[完整范围](../kernel363/REMAINING-CAMERA-SCOPE.md)推进，原厂数据优先。完整目标保持active。
