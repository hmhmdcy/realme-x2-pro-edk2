# 468：原厂长焦 mode2 已单模块接入并实机开流

本机19.2MHz原厂 **4208×2368 mode2** 已加入私有S5K3M5候选，两尺寸普通消费者自动选到该模式。2026-10-23新窗口r2实测720p／1080p各32帧，严格同SOF链路通过，随后恢复原传感器和正式440／434栈。没有新增pipeline传感器分支、Image/rootfs、SDK、刷写或重启；候选没有永久安装。

## 模式与驱动改动

[生成器](prepare-candidate.py)复用465的完整53条原厂写入，按原顺序追加到私有header；原初始化／mode3 header字节前缀及mode3 profile保持。新profile只追加尺寸、LL4848／FLL3312及LSC坐标，原厂core/golden、本机unit及其它IQ对象保持。原厂HFR标签和声明30fps同时保留，未改写为Normal／60fps。

原厂mode2是近16:9画幅，比例与精确16:9仍差约0.0422%。逻辑crop为`(0,376)/4208×2368`，LSC沿用既有mode0参考：first_quad=(0,188)、step=(1,1)。本轮解决467使用4:3 mode3缩放的问题，尚未实现精确等比中心crop或验收光学LSC准确度。

[单文件驱动增量](0001-media-s5k3m5-stock-mode2-format-cache.patch)还修正新增多模式暴露的控制顺序：ACTIVE S_FMT在共锁下先同步mode/state，停流时只更新控制缓存；开流沿用原厂表＋handler_setup统一编程，避免powered-idle按旧高度写出错误FLL。metadata控件不写寄存器，VBLANK内的曝光范围更新错误会立即返回。失败可能留下已改变的软件mode/state/部分范围，未宣称原子回滚。

[独立审查](REVIEW.md)核对原件、实际363 DTB、格式选择、LSC、控制时钟及API语义。[有限C检查](format-control-validation.json)执行实际两个回调及pad helper，28例ASan/UBSan通过；用候选双描述符喂给baseline回调，复现HBLANK `-EINVAL`被忽略和FLL2504。它是接口provider模型，不是内核并发或实际完整stream-on检查。

## 构建及原ABI

最终C SHA为`88251268b2c10e15116e717511da206e71da35ab359abb8ca80f747c44f2070b`；[已链接模块](module-build-validation.json)136152字节，SHA `494910c99ef116b88038ac3dfcc020a90aa35bfcc610b6b37c152601ee758392`，intree=Y、363 vermagic匹配。70个导入均在原363 Module.symvers，相关API头与原提交一致。原配置未启用MODVERSIONS，不把零CRC说成额外的符号版本证明。

独立稀疏source／O、j2、W=1/-Werror；正常in-tree modpost同时选择未改的v4l2-cci依赖，五个导出记录与363一致，其新产物未安装。仅为modpost私有复制335MiB vmlinux.o，不链接共享O、不重建它；构建后仍约6.04GiB可用，共享source／生成输入不变。

构建r1因遗漏模块化CCI provider而在modpost失败，原收据保留；r2已链接，但末尾检查误要求四个导出、实际为五个，使原脚本exit1。[缓存检查](inspect-module.py)按现成KO、日志、依赖与原ABI补审通过，没有重编来修报告。两种失败没有冒记成最初脚本全程通过。

## 实机消费与剩余缺口

| 输出 | 实读sensor | 消费／IPE | 数学／bootstrap | 消费SOF缺口 |
| --- | --- | ---: | ---: | --- |
| 1280×720 NV12 | 4208×2368 | 32／32 | 29／3 | 无 |
| 1920×1080 NV12 | 4208×2368 | 32／32 | 29／3 | 17、23、31 |

[原始严格审计](hardware-validation.json)不滤回执、不去重。同SOF FULL/PD10、前序GTM统计、WB revision及成功数学历史通过；每案32张LSC context均与对应参数revision／mesh-trace一致，分别涉及11／13个revision。此为参数／帧上下文核对，没有新增LSC硬件扰动或光学证明。1080另有一个未排队统计丢弃及四个stop未决统计，按真实历史计数保留。

两案各取得UID10000／CapEff0应用、隔离IPA／core／proxy映射和真实FULL FD证据。70次FULL qbuf／66次dqbuf，66条DQ唯一关联vb2 DQ，64张消费按实际管线TID、案内时间及SOF匹配；另两张FULL没有进入IPE／消费。八CPU overrun／commit-overrun／drop均0，专属实例清理，global/display/radio所选控制保持。

720p消费时间戳约30.014fps；1080消费约27.368fps，按SOF跨度归一约30.017fps，与候选默认帧节拍相符。这个短段不证明物理PLL时钟或曝光/增益2帧延迟。[缺口检查](gap-validation.json)确认三处有PD10/统计无FULL DQ、邻间仅后帧vb2 done；SOF17的邻DQ时窗queued/owned最低1，23／31最低0。DQ时间窗不等于物理SOF区间，不统一写成三个空队列或DMA根因。capacity因未绑定lens仍inactive，未改CPU／缓冲策略。

控制时钟仍为481930000，区别于CSI吞吐578560000。363实际DTB端点允许723200000Hz／四lane，实机成功开流是该候选的功能证据；无示波器时钟测量。原mode3较低link候选保持独立待验。主摄442的LTM因果按原范围保留，本轮没有长焦真实→黑→白→真实独立回放，也未验AWB锁定、AF、色准、编码录像或长期无丢帧。

## 事务与终态

r1被工具旧prefix在任何模块／客户端动作前拒绝，10个原件／原失败保留，不重放；[修正检查](runtime-tool-validation.json)核新prefix、plan/handoff、模块字典和加载/恢复顺序。r2是独立新预检／事务：先卸CAMSS释放notifier节点，再临时换sensor，恢复时先原sensor、再CAMSS。原sensor文件和loaded note、正式三模块／库／包均恢复，原文件从未覆盖。

worker14687实际退出、terminal/passed、failure/cleanup空，camera四项PM suspended、core／m2m闲置；PW14912／WP14915为UID10000／CapEff0，phoc3571／phosh3688保持。MONOTONIC非空日志fault0、taint0，临时用户目录／进程和trace实例均不存在。外部fresh两样本R8保持、保护有效、29.5℃、100mA／CC250mA／原电压上限不变；净0／+4mA仅两点，不称持续净充电或图标通过。手机已明确交回充电任务，相机仅离线后处理。

r2原件46文件、压缩包101998字节，SHA `44a6c8a51223445aa13355d4fca4039b42441eb9d707ec585b394f0cf971f204`；完整表、profile、源码、KO、日志和健康原件在私有kernel468。下一步可复用这个已开流的mode2补长焦LTM消费因果与控制延迟，再按缓存处理1080供给／耗时；多摄光学、AF及第五摄像头仍未完成。
