# 444：焦点／tone 合并同步调用，IPA6 与正常消费者验证通过

2026-10-23。延续 [443](../kernel443/README.md)的正常 GStreamer 16:9 路径，在独立源码新增 [0056](0056-camss-focused-ipe-dispatch.patch)：常见图像路径由两次同步 IPA 调用收敛为一次，保持既有焦点流程、原厂 tone 数学、同 SOF、实际 GTM／WB 与成功历史规则。四路共 480 帧逐帧通过，481 个入队作业均使用合并返回值，第二次 tone RPC 为 0。**帧率没有全面改善，CPU 焦点评估仍有长尾；旧 441 积压、长录像及完整多摄目标仍未完成，候选未永久安装。**

手机恢复正式 440 r32／r27、434 三模块及四份原有私有配置，模块 epoch 作业 0、taint 0、四设备 suspended，PipeWire／WirePlumber 各一个 uid10000。[恢复检查](current-state-validation.json)。本轮没有刷写、触发重启或写 NV／EEPROM，充电会话确认完全离线、不占用本轮手机与 SDK bind 窗口。

## 底层改动与边界

当前配对路径通常不调用 `frameMetadata`，其仅用于缺统计回退；常见同步往返来自 `processFocus` 和 `prepareIpeParameters`。新增私有 `prepareFocusedIpe` 入口在现有递归状态锁内依次调用这两个原函数，返回独立焦点状态、AF 元数据、镜头命令、tone 状态／字节／revision／fresh。

如果焦点函数发出实际镜头移动命令，合并入口**不准备 tone**；管线仍先执行镜头命令、发送原 `lensPositionApplied` 回执，再调用原 tone 入口。失败图像、无焦点及缺统计路径保留原调用；正常完成与物理成功回执仍是两个不同阶段，合并调用不提交数学历史。相对其它异步 IPA 事件，合并的两个步骤处于同一次调度内；没有声称所有旧并发交错都逐一等价。

私有协议由 5 升到 6，核心／代理／IPA 配套，核心仅接受版本 6。原来各入口仍在，保留 RAW／其它消费者的调用方式。只改 Mojom、管线及 IPA 三个生产文件；`processFocus`、`prepareIpeParameters` 函数体逐字节不变，其余已记录调校／数值源码不变，补丁零 fuzz／offset 重放。[源码验证](source-validation.json)。

0053 的请求／epoch／输入缓冲／请求序号所有权谓词与 442 相同，复用原 ASAN／UBSAN 证据；新旧焦点分支共用返回后的检查，元数据回退及 tone 回退检查保留。[边界核对](reentry-validation.json)。实机验证了正常停流，没有声称已专门强制覆盖每个 RPC 中途停流交错。

## 实际模块与构建

独立源码 `/mnt/samurai-full282/libcamera444-focused-ipe/src/libcamera-v0.7.2`，增量构建 135.59 秒、38 个 Ninja 步骤成功，SDK bind 已卸载。[构建](build-validation.json)。核心 SHA `8c8569c2…`，IPA `4c90047d…`，代理 `c7887708…`；[实际输入](runtime-inputs-validation.json)核对源、匹配 441 build4 三模块、签名及载荷。继续复用 443 的私有原厂 mode4 DS4 配置与同一 GStreamer 探针，未重建内核或改调校系数。

[ARM64 实际 IPA6 对照](focused-module-validation.json)在 3456／2592 两个输入高度各比较 13 次“分开／合并”调用：返回码、AF 元数据、镜头命令、tone 状态、revision／fresh 和完整 6008 字节包完全相同。覆盖 GTM bootstrap／实际 ACK、缺 lux、失败不提交／成功提交、镜头移动延后 tone，以及停止／旧 epoch 拒绝。统计是合成夹具，不是硬件实拍；最初夹具使用时间戳 0 和 4:3 固定人口，分别被原 AF／统计校验拒绝，修正为有效单调时间与按输入几何计算人口后通过，没有改生产规则迁就夹具。

## 正常消费者实机与时延

四路仍由实际 `libcamerasrc → appsink` 接收 NV12，内核 offset 对应同 SOF PD10、有效 GTM／WB context 和成功 receipt。确认实际传感器 4608×2592、候选核心映射、正式 r32 GStreamer 插件，以及普通／隔离进程关系。[逐帧验收](hardware-validation.json)、[事务摘要](runtime-r1-validation.json)。

| 路径 | 消费帧 | 成功数学／bootstrap | 物理 IPE | 合并调用用于入队 | 前8样本后 PTS fps |
| --- | ---: | ---: | ---: | ---: | ---: |
| 720p 普通 IPA | 120 | 116／4 | 120 | 120 | 29.787 |
| 720p 隔离 IPA | 120 | 117／3 | 120 | 120 | 29.524 |
| 1080p 普通 IPA | 120 | 117／3 | 121 | 121 | 30.056 |
| 1080p 隔离 IPA | 120 | 117／3 | 120 | 120 | 29.787 |

共 480 成功帧＝467 次数学提交＋13 张 bootstrap、481 物理 IPE 完成；多出的一个 1080p 普通作业在停流取消，未 commit。每路 3 个停止取消请求，源端成功但 appsink 未消费差值均为 0；观察丢弃／停止未决与图像分开计数，最终 pending／superseded 为 0，新内核故障 0。

新增分段计时显示：焦点 CPU 测量中位 9.98—13.47 ms，合并分派中位普通约 0.83—0.85 ms、隔离约 5.03—6.11 ms，复用缓存 tone 约 0.006 ms；焦点测量最大出现 50—92 ms，包含启动和调度影响。不能将墙钟区间全部解释为纯计算成本。[时延](latency-validation.json)。

对比 443，隔离 Pair→queue 中位 720p 24.641→22.488 ms、1080p 21.205→15.812 ms；普通两路约 11 ms。前 8 样本后仍分别跳过 1／2／0／1 个 SOF。各轮照明、调度与温度没有受控，帧率有升有降，**不能据此认证普遍吞吐改善或无丢帧长录像**；可直接确认的是 481 个入队作业只做一次合并调用。[有界对照](comparison-validation.json)。

## 保存与续作

原厂资料、系数、参数包、合成夹具原件及完整日志仅在 `E:/edk2-samurai-out/kernel444` 与手机 `/var/lib/samurai/k444-focused-gst-r1`。事务已终态，勿重启旧事务。442 的完整像素／LTM 因果与 RAW-only／双流证据、443 的 mode4 原厂绑定证据保留；本轮没有重新做全部模组／模式或绝对画质验收。

下一步细分焦点测量中的 DMA 同步、映射、ROI 算法及调度等待，优先把 CameraManager 关键路径的长尾收敛到有界工作；不能简单跳过公开 FoM／AF 行为或扩大统计池。协议6候选仍需按改动覆盖其它消费者／模组和实际 AF，再决定发布。持续录像、HDR、光学校准、第五2MP与多摄几何／同步等完整范围继续。下一手机或刷写窗口仍与充电会话协调。
