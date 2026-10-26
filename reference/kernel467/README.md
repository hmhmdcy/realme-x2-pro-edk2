# 467：长焦 mode3 两尺寸同帧双遍实际消费

2026-10-23，`k467-tele-r1` 已实际完成并恢复正式440／434组合。复用461 core、444 IPA6／旧proxy／签名、441三模块、440长焦原厂profile和449正常GStreamer客户端，未重编客户端、SDK、Image或rootfs。两案均为UID10000／CapEff0的隔离IPA消费者；没有重放历史worker。

| 实际输出 | 消费／IPE完成 | 数学／bootstrap | 消费SOF缺口 |
| --- | ---: | ---: | --- |
| 1280×720 NV12 | 32／32 | 29／3 | 无 |
| 1920×1080 NV12 | 32／32 | 29／3 | 14、21、28 |

[严格审计](hardware-validation.json)复用443的逐SOF／调校历史检查，仅显式改变model和32帧目标；全部原始回执保留，未过滤或去重。两案FULL／PD10、GTM bank／前序统计、WB revision及成功数学历史一致。1080p另有一个未排队统计丢弃和四个stop时未决统计，按真实回执／历史计数核对，没有算成成功图。未通过AWB锁定、色准或光学验收。

实际首帧G_FMT均为 **2104×1560 mode3**、mbus code12298。NV12字节数分别1382400／3110400，全部消费buffer的抽样hash非零。此处是已有4:3模式缩放到两尺寸，**不代表原厂近16:9 mode2已接入**。[465](../kernel465/README.md)保留mode2全表／IQ增量，[466](../kernel466/README.md)继续核时钟候选。

## FULL证据及剩余缺口

沿用463的媒体图／角色门槛，现场确认PIX source1到实际FULL节点及每案应用的真实字符FD；两次实际/proc还核了候选core、隔离IPA模块／proxy与UID。实例跟踪有70次FULL qbuf、65次dqbuf，65条DQ均唯一关联对应vb2 DQ；64张消费图按案内单调时间、实际管线TID及SOF唯一匹配FULL DQ。另一个FULL已DQ而未进入IPE／消费，保留区别。

八CPU overrun／commit-overrun／drop全0，专属实例已删除，global/display/radio所选控制不变。[缓存缺口检查](gap-validation.json)显示三次缺SOF都有PD10和统计，没有成功FULL DQ；邻帧之间仅有后一个FULL vb2完成，queued／owned软件快照最低0，邻DQ间隔约66ms。尚无物理SOF边沿／硬件bank证据，不能据此认定DMA、驱动或哪段用户态处理为根因。

长焦没有已部署lens绑定，本次capacity日志是inactive；461源码的租约只在lensActive时取得，未把主摄已有租约覆盖冒认成长焦也启用。当前没有为这三次缺口改变CPU亲和、缓冲数量、内核或原厂数学。下一性能增量可先按缓存定位处理耗时与请求供给，再选择受影响改动。464的应用图像拷贝结论仅适用于461 lifecycle，不直接外推本次低拷贝消费者。

GStreamer PTS与原内核timestamp的偏移跨度分别1534／3088ns，检查保留观测值，没有断言两者逐纳秒相同。检查器初版误设固定偏移、并误要求长焦也启用租约，均在缓存核对后修正；硬件事务和原件未重跑或改写。

## 终态与适用范围

worker12415实际退出、terminal／passed、failure及cleanup均空；正式库／包／模块、camera四项PM、core／m2m已恢复，临时用户目录与进程不存在。PW12628／WP12634为UID10000／CapEff0；phoc3571／phosh3688保持。MONOTONIC区间内非空内核日志fault0、taint0。

外部只读终态两份fresh样本均managed／protection有效、29.3℃；R8 manifest320316c3…及三个loaded note、SDP/native100mA、CC250mA及电压上限保持。两次净电流−28／−4mA，没有称持续净充电或图标通过。手机窗口已明确交回充电任务，相机只做离线后处理。

本轮证明长焦两尺寸的同帧双遍消费和原厂参数历史。主摄[442 LTM扰动因果](../kernel442/README.md)按原范围保留；本轮没有长焦真实→黑→白→真实独立回放，不能把它写成长焦自身因果实测。录像、正常画幅、AF、画质、长期和多摄目标仍未完成。

工具：[预检适配](preflight-handoff.py)、[本地准备](prepare-runtime.py)、[手机body](capture-body-tele.py)、[原件审计](inspect-tele.py)、[缺口检查](inspect-gaps.py)。这些文件不是重放入口；已结束事务不可再次launch。42个原件、运行载荷、完整日志和终态健康在私有kernel467；原件压缩包100808字节，SHA256 `c1275fc59858ec9c0f1b279416881a4f9e1bc2c0bba28fad1cc349239bb1cf2e`。原厂系数／个人数据继续私存。
