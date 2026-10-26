342当前：r27/config-r22已部署，CAMSS338保持。已合入个体WB/CCT、实时lux驱动CCM及动态LSC；四摄安装后显式配置通过，默认YAML无个体表。实际模式曝光表选择及正常光学校准继续。[342证据](../../../reference/kernel342/README.md)。以下为历史。

321当前：r26/config-r21已部署，318 CAMSS保持。LSC的IPA合成、模式重采样及启动参数上传完成，真实内部图案链路通过；默认个体LSC尚未启用。四摄取流及安装后GStreamer／PipeWire通过，正式光学与多摄校准仍在继续。[321证据](../../../reference/kernel321/README.md)。以下为历史。

316当前：r25/config-r20与314 CAMSS已部署，默认选择硬件管线。四摄GStreamer NV12、主1080p／前720p、四摄RAW和安装后PipeWire NV12通过；315的双流／AE／AWB／单次AF证据沿用。完整画质校准、多摄同步与连续AF未完成。[316证据](../../../reference/kernel316/README.md)。以下为历史。

278当前：r24/config-r19已部署通用单次AF、帧携带清晰度统计与串号回执的标准镜头控制，原生触发/取消/重触发/停流及自动曝光下AF通过。模组行程/搜索参数仅在设备数据包。配对测试单次AF约9–12秒，仍需加速；连续AF、距离标定、完整画质、GUI/录像和Spectra未完成。[278证据](../../../reference/kernel278/README.md)。以下按历史阶段阅读。

277当前：r23/config-r18已部署通用RAW空间清晰度统计和标准FocusFoM，主摄同请求RAW重算与元数据逐帧一致，失焦与恢复对照通过；保留完整功能。AF搜索/距离标定、GUI/录像和Spectra仍未完成。[实际部署](../../../reference/kernel277/README.md)。以下按历史阶段阅读。

276当前部署：libcamera r22/config-r17，新增通用 Simple 镜头流生命周期；CameraManager常驻枚举四摄后镜头fd释放，供电/时钟回收。标准V4L2手动对焦已有光学响应，四摄238帧回归通过；AF算法、画质、GUI/录像、Spectra及r22完整手动曝光矩阵仍待验收。[现机证据](../../../reference/kernel276/README.md)。以下为历史阶段。

273已部署：libcamera r21/config-r16 新增 GW1 原生增益 helper。主摄 RAW/RGB 与600帧CPU JPEG已出帧，四 sensor 238帧交替通过；高分辨率手动切换测试仍失败，AF/画质/GUI/Spectra未完成。[部署及失败范围](../../../reference/kernel273/README.md)。以下为历史阶段。

271（2026-10-18）：当前原生部署libcamera r20/config-r15，新增标准S5K3M5原生gain code/32 helper，配套内核控件32…512。481码factory测试、96组物理细分增益、三摄193帧与600帧普通预览通过；初始AE慢、画质/AF/GUI/主摄/ISP仍开放。必须和新sensor模块配套更新或回退。[271](../../../reference/kernel271/README.md)、[当前源锁](source-lock.json)。下列r19及更早叙述按历史解释。

# libcamera 99990.7.2-r19：公共相机补丁集

当前配方及原生部署为r19/config-r14。完整保留r15的22补丁和功能，仅新增0023修复Simple管线在其它进程改变MC图后缓存失效的链路设置；没有机型/应用判断。13包完整构建及签名/运行QA、七包原生升级、跨进程交替、Snapshot前后摄预览/界面切换/快门与JPEG解码通过。[268结果与边界](../../../reference/kernel268/README.md)、[当前输入锁](source-lock.json)。仍用既有CPU ISP及Cairo显示回退，默认GPU、画质和完整rootfs开放。以下r15数字为历史。

当前配方及实际部署为r15/config-r10，保留auto,virtual完整管线、11框架子包、tuning/desktop和原20补丁。0021补IMX319 gain helper，0022在同步IPA start后快照初始参数并补combinedMatrix，记录CPU实际处理帧身份，不改黑电平或调校。[22补丁源锁](source-lock.json)、[239构建与部署](../../../reference/kernel239/README.md)。

13包/34AArch64 ELF/5IPA签名与Qt/Python/GStreamer等QA通过，实际只升级七个运行包。候选和系统默认路径各两次start/24帧，首参正确；候选前摄RAW/RGB各六帧回归通过。后摄仍有全零帧，严格失败及光学/颜色待办保留，不以非零灰底验收。

CPU独立曝光/增益Auto/Manual、RAW-only统计及停止取消修复保持；225的大规模回归属于[历史r13证据](../../../reference/kernel225/README.md)，不能冒充r15全矩阵重测。16MP实验默认关闭，GPU ISP和完整kernel/rootfs仍开放。

外部原IPA214/APK203密钥复用，strip后重签IPA，私钥不入仓库。r15→r13/config-r8使用实际225七包和239事务前world/repo/配置；原生降级模拟通过，未完整往返，内核e49/ff9等保持。
