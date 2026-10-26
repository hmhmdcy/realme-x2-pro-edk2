# 441：720p／1080p 同帧 PD10 与 LTM 消费已取得实证，候选整体验收未通过

2026-10-23。主摄两种尺寸均已完成普通／隔离 IPA 自动双遍实拍，并取得固定 FULL、仅改变 PD10 的 LTM 消费证据；同时修复了隔离 IPA 停流重入导致的用户态崩溃。**最终候选 r7 在 720p 隔离路径出现统计积压、错误帧与配对超时，不能发布为通过版本。** 手机已恢复正式 440 r32／r27 与 434 三模块，当前模块 epoch 作业 0、taint 0、资源休眠、两个桌面服务各一个。[最终恢复](current-state-validation.json)、[最终候选结论](hardware-validation.json)。

## 原厂数据与尺寸链路

复用 437／440 已核对的主摄 4608×3456 私有原厂配置，未重新读取 EEPROM／NV，未改调校数学、系数、IPA5 协议、传感器模式或板级 DT。原厂完整 striping、DC 网格、最终 pass distributor／BL 输出已与实际 C 比较，不能把该离线比较单独当作硬件完成证据。[原生 BL](native-bl-validation.json)、[公共布局](userspace-layout-validation.json)。

| 处理输出 | FULL 字节 | PD10 尺寸／stride／字节 | 原厂 DC／FULL stripe mask |
| --- | ---: | --- | --- |
| 1280×720 | 1382400 | 320×180／1344／123648 | 1／15 |
| 1920×1080 | 3110400 | 480×270／1920／261120 | 3／63 |

内核按实际 quarter 布局配置两个源平面和输出容量；通用管线移除 640×480 限制，保留 RAW-only 消费者判断、同 SOF FULL／PD10 配对和缓冲所有权。候选内核的粗级容量仍有 256 KiB 上界；这不是任意尺寸、录像帧率或其它三个模组已验收的声明。

## 实拍与 LTM 因果证据

r5 使用与最终候选相同的最终用户态载荷（build5 与 build2 的核心逐字节一致），内核尚未增加最后的辅助恢复状态分类。该轮成功图像如下；因一条统计输出缺标记录，整轮没有被写成通过。[逐帧证据](hardware-feature-validation.json)、[原始事务](runtime-r5-validation.json)。

| r5 路径 | 成功图像 | 数学提交 | bootstrap |
| --- | ---: | ---: | ---: |
| 720p 普通 IPA | 51 | 48 | 3 |
| 720p 隔离 IPA | 53 | 49 | 4 |
| 1080p 普通 IPA | 54 | 50 | 4 |
| 1080p 隔离 IPA | 39 | 36 | 3 |

逐帧核对真实 PD10 SOF、已实际生效的 GTM cookie／generation、WB、上次成功 lux 与最终历史；共 197 张成功图像、183 次数学提交、14 张明确 bootstrap。每路末尾连续 8 帧 AWB locked。53／54 等应用图像数与物理完成计数分开：另有一份已入队作业在停流取消，未推进数学历史。

两种尺寸分别执行“真实 PD10→中性黑→中性白→再次真实 PD10”四作业，FULL、参数包不变，ANR／TF 关闭。首尾输出逐字节一致，也与对应实拍图像一致；只改变 PD10 就改变最终 FULL 输出，提供 LTM 实际消费的因果证据。r5 共 206 次物理 IPE 完成，未与其它事务累计。scratch 仍为预填内容，**没有导出或冒认片内 DC 平均值 SRAM 表**。画面结构已查看，仍有柔软／雾感，绝对画质未验收。

## 本轮修复与未通过实验

- r1／r2 的 1080p 隔离路径分别在退出时 SIGSEGV／`map::at` 异常。匹配 core 回溯定位 `finish()` 在同步 `processFocus()` 期间重入停流，请求被清除后继续执行。[0053](0053-camss-finish-stop-reentry.patch)让取消跳过新的 IPA 工作，并在三个同步调用后检查 epoch、请求存活、输入及请求序号；r3—r6 和 r7 的失败停流均正常退出。[ASan／UBSan 检查](reentry-validation.json)。
- r3／r5 的旧缺标错误、r5 pad4 统计及 r6 pad2 DS4 诊断均保留。把统计池从 4 增到请求数＋4 的 [0054 实验](0054-camss-ipe-statistics-backlog.patch)未解决另一辅助输出的恢复边界，已经撤销，最终源码没有该补丁。
- [辅助恢复候选](aux-restart-sof.patch)仅为空辅助 FIFO 的重启建立状态：无标签缓冲仍返回 `VB2_BUF_STATE_ERROR`，首个有效标签结束恢复，主输出及正常运行中的缺标仍报错；没有猜测 SOF、GTM 版本或增加 MMIO 读取。[软件合约](aux-restart-validation.json)通过，但该分支尚缺稳定的完整实机验收。
- 最终 r7 的 720p 普通路径 49 帧正常；720p 隔离路径第 5 个应用回调携带错误缓冲（只有 4 次成功历史），继而退出，1080p 和 replay 未继续。日志显示图像 SOF11 等待时统计已推进到 SOF25，出现明显积压。没有把失败缓冲计成成功图像。[r7](runtime-r7-validation.json)。

所有事务都已终态、恢复正式模块和服务；r7 新内核故障 0，不能因此宣布应用链路通过。完整日志、core、原厂资料、参数、FULL／PD10 和照片仅存私有 `E:/edk2-samurai-out/kernel441` 与手机对应事务目录，旧事务不可重启。

## 源码、构建和续作

用户态保留独立 `libcamera441-variable-pd10`，最终只叠 0052／0053；内核在 434 基线上叠可变几何、软件队列诊断与辅助重启分类。两侧补丁均零 fuzz／offset 重放。[源状态](source-state.json)、[内核状态](kernel-source-state.json)、[重放](patch-chain-validation.json)。内核匹配模块 W=1／Werror 通过，共享构建输出恢复；最终 libcamera build5 成功、IPA 与代理未变、签名通过。[模块](intree-build-validation.json)、[用户态](build-validation.json)、[实际输入](runtime-inputs-validation.json)。未修改正式软件包配方或永久安装候选。

下一步只复现受影响的隔离路径，记录 FULL／PD10 到达、统计回调、同步 focus／参数调用及 IPE 完成时延，优先把配对关键路径中的同步阻塞收敛为有界调度。继续保持严格同 SOF、实际 GTM／WB 版本和失败不提交；不要用无限缓冲、放宽计数或重放旧事务消除报告。稳定后再补其它模组、持续录像帧率／更多尺寸以及完整光学范围。
