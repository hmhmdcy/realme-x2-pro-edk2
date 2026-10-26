# 271：长焦原生细分增益、配套部署与自动曝光实测

2026-10-18。上一轮属于进展：270用户确认摆好场景后，首次获得长焦可辨认实景，仍欠曝。本轮继续真实摄像头适配，完成驱动与公共libcamera配套修复、原生软件包部署和物理响应验证。**完整多摄、主摄、AF、画质、GUI、录像和Spectra硬件ISP仍未完成，目标保持active。**

## 当前部署

boot270/Image183和当前启动保持，`7.3.0-rc6-rmx1931-samurai-k132+`，774模块/961包；没有刷写或重启。仅S5K3M5模块从22315c6f…更新为`11791431fb7d50ccd64163fdc5d753b61be5844830e90d14ce4f738a42f8b8f5`，其它773模块逐字保持。五个libcamera组件升为99990.7.2-r20，config/stack为0.1.0-r15；其余954个包记录保持。PW15740/start358174、WP15743/start358179，桌面Phoc3543/Phosh3786保持；续作仍需核实际身份。

运输用本目录host.py，复用270严格原SSH密钥和当前boot guard `/var/lib/samurai/k270-work/boot-id-private.txt`。服务身份见手机`/var/lib/samurai/k271-services-current-private.json`，旧270服务PID5177/5179已失效。boot270的DT与Image不因这次模块更新变为271统一内核；269完整Image/773模块候选仍未部署，完整最新rootfs未重建。

驱动V4L2增益单位和libcamera helper必须配套：新内核控件32…512对应1…16倍，helper使用code/32。不能只把旧r19库与新模块混装。配方、模块与部署锁见[源配方](../../linux-port/packages/libcamera/README.md)、[部署锁](../../linux-port/camera/deployment-lock.json)。

## 原厂依据与修复

对本机原厂S5K3M5传感器库重新核对了固定指令：增益范围1…16，寄存器码floor(gain×32)、最大512、实际倍率code/32，步进1/32。原库仅离线读取/反汇编，没有执行或修改，也未操作校准/NV。[原厂依据](factory-gain-validation.json)。

原驱动仅暴露整数1…16，再左移5位写寄存器，丢失细分增益。现在控件暴露原生32…512、步长1，直接写寄存器。公共libcamera新增标准`s5k3m5` helper，使用线性码/32；没有机型/应用判断，不编造黑电平。供电、GPIO、时钟、模式表、其它sensor helper保持。[补丁](s5k3m5-native-gain-code.patch)、[helper](0024-s5k3m5-native-gain-helper.patch)、[源锁](gain-source-validation.json)。

本地维护树camera270-kernel分支samurai-camera-gain271，提交`ac7ccc2da924b44aa6dff5d1be24356253890ee8`，工作树清洁；270和camera-common分支保留，未推送。[提交](kernel-commit-validation.json)。24MHz配置同样改用原生增益码，但没有24MHz实机回归，不能扩写本机测试范围。

## 构建与部署验证

匹配Image183的树内sensor/CCI目标W=1零诊断、vermagic/导入符号通过；CCI字节与现机一致，不替换CCI；canonical构建树按原内容恢复。[模块](current-module-build-validation.json)。13个完整功能签名APK通过，34个ARM64 ELF、Qt/Python/GStreamer等入口和五个IPA签名核验；使用保留r19源码/对象执行原生abuild build/rootpkg/index，不称全新解包SDK或完整rootfs重建。[构建](r20-package-build-validation.json)、[完整QA](complete-host-qa-validation.json)。

实际编译后的libipa factory验证481个原生码的精确往返、1/32步进及前/后摄helper保持；旧r19缺helper的负向对照失败符合预期。[helper测试](gain-helper-test-validation.json)。

七个旧/新APK及索引原生验签、七包升级模拟、原49项载荷及模块库存核验通过；匹配回退已保存手机/PC两份，共2815504字节，SHA256 `d69a679ae8afdb2aae485ba605b5f3348cc76a8d0df9f9ee1cf8a296d6b14bb0`。该回退包含原r19/r14签名包、模块及配置，只有降级模拟通过，未声称实际完整往返。[预检](gain-preflight-validation.json)、[回退](gain-rollback-validation.json)。

第一次事务在停止WP后的退出检查处中止，尚未发包事务或解绑/替换模块；当时未记录瞬态进程状态，不能证明有真实自动重启。已确认原worker终止、库/模块/数据库保持，恢复旧WP。第二次使用新事务目录，排除僵尸进程并等待正常退出后继续：正常解绑S5K3M5、仅卸载其自身模块，更新七包和模块，加载note与磁盘一致，再启动标准PW/WP；共享CAMSS/CCI/PMIC未卸载，桌面未重启。[失败后恢复](preflight-recovery-validation.json)、[实际配套事务](gain-install-r2-validation.json)。旧上下文均已终态，不能重放。

首次新probe上传因基线probe目录已存在，在mkdir处失败，尚未写新二进制或创建采集上下文；改为独立fractional目录后上传并按哈希核验成功。相关失败日志保留私人目录。基线手动测试结束1秒时CCI1仍active，随后独立观察确认为suspended；不篡改首次健康失败值，也没有用重启处理。[基线](baseline-manual-r1-validation.json)、[自然回收](baseline-settled-r1-validation.json)。

## 物理结果

同request RAW2104×1560和RGB2048×1536配对，元数据序号/时间戳一致，按有效行解析MIPI RAW10并执行DMA同步；每档12帧、后6帧稳态分析，像素不写公共输出。

| 档位，约32ms曝光 | RAW均值 |
| --- | --- |
| 1倍 | 90.39415 |
| 1.03125倍 | 91.21065 |
| 1.5倍 | 103.5995 |
| 2倍 | 116.8505 |
| 4倍 | 169.6575 |
| 8倍 | 275.305 |
| 返回1倍 | 90.3878 |

96组配对完整通过，捕获元数据精确对应细分倍率；未饱和档位线性拟合最大均值残差0.0331 DN，截距63.9857仅是本场景拟合，**不是写入驱动的黑电平或绝对ISO标定**。16倍档约3.8%接近RAW饱和，保留事实。[实测](fractional-manual-r1-validation.json)、[响应分析](gain-response-validation.json)。

原整数栈96组曝光/增益基线同样证明整数控制有效，不能说原驱动无法增亮。旧180组自动曝光才接近33.2ms，新栈360组已到约5.56…5.81倍，仍在收敛。RAM全帧统计probe约15个交付帧/秒、可有跳序，不把它误称sensor只有15fps或完整30fps验收。[旧自动](baseline-auto-r1-validation.json)、[新自动](fractional-auto-r1-validation.json)。

普通原生libcamerasrc→CPU JPEG连续600帧、PTS跨度约19.94秒，保存36/180/600帧私人JPEG。核看36帧仍明显欠曝，600帧已明亮、可清楚辨认场景细节；自动曝光收敛慢、色彩/噪声/AF未验收。没有把长预览的亮度改善全部归因于增益补丁，也没有改gamma代替曝光控制。[普通取流](ae-warmup-validation.json)、[光学核看](ae-optical-review.json)。

新栈标准cam三摄14段交替、长焦SIGINT正常退出和重开，共193帧全部通过，无强杀、期间无服务重启。[三摄回归](three-camera-regression-validation.json)。最终三sensor/双CCI/CAMSS suspended，六电源disabled/users0，三MCLK关闭，taint0及全boot所列fault0，桌面身份保持。[最终状态](final-r1-validation.json)。当前pstore空不抹除旧Snapshot/modem watchdog故障。

## 继续完整适配

- 改善首次AE速度并验证稳定、光照变化和前后切换；审查控制延迟、时序与真实裁剪/静态属性，继续色彩/噪声/方向调校及AF。
- 标准GUI三摄选择、录像编码、更多模式/长稳、GPU软件ISP仍未完成。GUI前后切换/快门只有旧r19对应启动的证据，不自动晋升r20三摄GUI。
- GW1主摄Sunny/Qtech数据两种视图交叉核对已完成，仍未建立主摄driver/上电/C-PHY/AF；候选其它后摄的实际型号仍待确认。
- Qualcomm CSIPHY/CSID/VFE RDI负责RAW采集，成像处理仍CPU software ISP；Spectra硬件处理没有接通。完整Image/模块/rootfs统一构建、上游提交和跨版本更新仍开放。

私人原图、库反汇编、环境、原始日志、签名输入和启动身份在E:/edk2-samurai-out/kernel271及手机k271目录；公共仓库只保存源、配方和脱敏证据。
