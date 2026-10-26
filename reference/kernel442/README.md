# 442：停止取消语义修复，两种尺寸同帧 PD10／LTM 全链路通过

2026-10-23。延续 [441](../kernel441/README.md)，本轮在主摄 4608×3456 原厂模式下完成 720p／1080p、普通／隔离 IPA 的自动双遍和 LTM 因果回放，并通过 RAW-only／双流停流回归。**新增生产改动只有 0055 停止取消状态修复；此前 441 的罕见统计积压根因仍未关闭，候选未永久安装。** 手机保持正式 440 r32／r27、434 三模块与四份原厂私有配置；epoch 作业 0、taint 0、资源休眠、桌面服务恢复。[逐帧验收](hardware-validation.json)、[最终状态](current-state-validation.json)。

## 底层修复与调度对照

现有 libcamera `Request::Private::completeBuffer()` 只有收到 `FrameCancelled` 才把请求标为 `RequestCancelled`。旧 CAMSS 在 `running_ == false` 停止清队列时仍回传 `FrameError`，标准异步消费者会将这些请求当作普通完成处理。r3 使用旧 441 核心，50 张成功图像后又收到 3 个停流错误回调，事务失败并正常恢复；这与运行期间的配对超时分别记录。

[0055](0055-camss-stop-cancel-status.patch)只在停止状态为图像及 RAW 缓冲设置 `FrameCancelled`，保留运行期间的 `FrameError`、同 SOF 身份与失败不提交。只改一个管线文件，零 fuzz／offset 重放，受影响核心增量构建成功；IPA、代理、签名、协议 5、数学和原厂配置逐字节不变。[源核对](source-validation.json)、[构建](build-validation.json)、[实际输入](runtime-inputs-validation.json)。复用 441 最终 build4 匹配三模块及其原厂 striping／BL、几何和边界验证，没有重建内核或修改 MMIO。

现有 cam 应用在 `src/apps/cam/camera_session.cpp` 把完成后的处理投递到应用事件循环。原探针直接在 CameraManager 线程复制、计算均值及写文件；r1 实测复制／均值中位 7.278 ms、写入 0.915 ms。本轮探针按现有 cam 的方式把处理放到应用主线程，队列受 4 个请求自然约束，每张成功图像仍保存并审计。这是验证工具修正，不能当成已实现底层 IPA 异步化。

同一探针可选择直接／应用队列方式，只在首张处理前注入 0／200／500 ms 暂停。新核心的 r4—r8 均通过，队列峰值 1—3；200／500 ms 的直接与队列对照均未稳定复现旧积压。场景与收敛帧数不同，不从交付帧数推断吞吐提升，也不宣称关闭持续统计积压。[时延与对照](callback-controls-validation.json)。r2 仅暂存、从未运行，旧事务不重放。

## r9 实机与逐帧结果

使用最终 442 核心、同一探针的应用队列模式且不注入暂停，四路均完成并逐张核对 NV12 长度／均值、FULL／PD10 同 SOF、实际 GTM cookie／generation、WB、成功 lux 和历史提交。每路末尾连续 8 帧 AWB locked。

| 自动双遍路径 | 成功图像 | 成功数学 | bootstrap | 物理 IPE 完成 |
| --- | ---: | ---: | ---: | ---: |
| 720p 普通 IPA | 52 | 49 | 3 | 52 |
| 720p 隔离 IPA | 63 | 59 | 4 | 63 |
| 1080p 普通 IPA | 53 | 50 | 3 | 54 |
| 1080p 隔离 IPA | 51 | 47 | 4 | 51 |

合计 219 张成功图像、205 次数学提交、14 张 bootstrap；1080p 普通路径另有一个已物理完成但停流取消的作业，未提交成功历史。全部 6 个捕获会话各返回 3 个明确的停止取消请求，未将它们计为交付图像。[完整事务](runtime-r9-validation.json)。

两种尺寸分别固定 FULL 和参数，执行“真实 PD10→中性黑→中性白→再次真实 PD10”各 4 作业。三个不同 PD10 得到三个不同输出；真实输入首尾结果与对应实拍逐字节一致，确认 LTM 实际消费。没有声称导出片内 DC SRAM；几何／容量沿用 [441 表格](../kernel441/README.md#原厂数据与尺寸链路)。

RAW-only 6 帧没有 IPE、PD10 或虚构数学历史；RAW＋640×480 NV12 双流 6 帧按同 SOF 配对、6 次 IPE 完成。整轮物理 IPE 共 234 次：自动 220、回放 8、双流 6。停止未决观察、取消和成功历史分别核对，最终 pending／superseded 为 0，新内核故障 0。

两个应用帧日志被完整的并发 stderr 日志插入拆开；审计只重组原有字节，保留插入事件和全部字段检查，原始文件未改。其它同 SOF／GTM／历史及像素审计沿用 441，没有放宽验收或重新采集。

## 保存与续作

源码 `/mnt/samurai-full282/libcamera442-bounded-dispatch/src/libcamera-v0.7.2`，核心 SHA `f7c25ff3818b95954cfe7cc310d21f3b406225860abf20bb44e32ee66f5ad704`。目录名称不表示底层调度根因已关闭。原厂主摄配置继续复用 437／440，未重读 EEPROM／NV、替换个体数据或修改传感器／DT／调校。原件、系数、像素和完整日志只在 `E:/edk2-samurai-out/kernel442` 及手机 `/var/lib/samurai/k442-callback-timing-rN`；r1、r3—r9 已终态恢复，不得重启旧事务。未刷写、触发重启或 push。

下一步在正常消费者或再次出现积压时对照 FULL／PD10／统计、同步 focus／参数及 IPE 完成时序，判断持续阻塞的来源；只在证据指向的层修复，不扩大统计池或放宽身份检查。保留本轮通过结果，按改动范围选择后续验证，再决定打包安装。其它模组／模式、持续录像帧率、绝对画质、连续 AF、第五 2MP 和多摄几何／同步仍在完整目标内。
