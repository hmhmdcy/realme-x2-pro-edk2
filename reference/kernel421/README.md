# 421：真实统计观测、最终图像回执与统计发布重入修复

完整多摄/骁龙ISP目标继续active。本轮将真实同SOF统计、曝光/增益和IFE参数版本接到逐帧事务，并修复同步IPA调参期间过早判定统计缺失的重入问题。**当前提交的是观测历史，不是TMC/LTM数值状态；自动非零IPE参数仍未生成。** 候选临时验证后退出，正式系统仍为420部署的419驱动与r31/r26，没有安装候选IPA2。

## 接入层次及生命周期

复用已有libcamera IPA、统计解析、DelayedControls、CamssIpe及标准Media Request链路，未重复下载固件或扩大已通过的原厂算法矩阵。原厂数值依据仍复用407..416；本轮补实际输入和结果归属。仅改用户空间四文件：[完整补丁](0042-camss-ipe-frame-history.patch)、[零fuzz复现](source-validation.json)。SoC、板级DT、传感器、主线内核/驱动、6008字节内核UAPI保持。

`IpeFrameObservation`拥有1024个BHIST计数及其同SOF实际曝光行、增益码、物理曝光纳秒/增益、控制来源、IFE revision、可用lux/exposureIndex和Gamma override标记；不持有会复用的统计DMA缓冲指针。`Statistics`事件携带token及核对摘要，pipeline在图像/统计配对时认领token，最终`tryComplete()`完成图像和RAW时间戳配对后才反馈成功或失败。RAW-only不提交IPE历史；缺统计时既有元数据恢复不伪造token。

[事务类](ipe_frame_history.h)上限64份，epoch及单调token拒旧结果，失败只丢本事务，后到的旧SOF成功结果标记superseded、不能回退历史，停流清所有待定观测。SHA并非本轮摘要算法；日志用FNV校验标识，硬件验证结论是摘要一致，完整数组复制的不可变性由模型检查。Gamma override标记不等于已经证明IPE输入传递域；不要把这些观测当成原厂HDR双曝光槽、DRC/darkGain或408未知raw124/140字段。

私有IPA接口版本从1升2，生成库、IPA、代理匹配使用；YAML版本和内核UAPI不变。当前候选库SHA256 `9fb54db05e713f165dd00a203fa3c0e509f0a56ab1f3d7986a80afb60ae16597`，IPA `ced9de9043e095314a7e3662f5bf56e26e6f88e356bbd6f3ce9312d67528e9f2`，proxy `15ec5035df641782ec189d088d36768525896e868a21ea39020f5f2f89bd4973`。[构建](build-validation.json)、[签名](signature-validation.json)。构建按实际新增字段和修复变化进行三次，旧报告保留；原签名私钥不进入仓库。

## 发现并修复的现有回调顺序问题

r1主摄图像12帧成功，但13份观测仅10份与图像配对/提交，另3份停流丢弃；其中SOF1/2已有有效观测，却走`Image controls recovered`。核对实际`statsProcessed()`与`queueIspUpdate()`：先erase pending，再同步`prepareParameters()`，而直方图尚未发布；代理等待期间递归处理相机事件，使`completeMissingStatistics()`误以为该帧无pending也无histogram。

修复将匹配直方图发布及认领提前到同步参数准备之前，并在可能递归处理事件的调用返回后检查running/epoch。参数准备若期间停流，停止使用已释放的参数buffer。没有放宽统计大小、帧身份、传感器控制范围、RAW配对或内核错误判断。

[34个事务/实际aggregate模型](history-validation.json)与[11个实际统计/参数队列函数模型](statistics-reentry-validation.json)全部ASan/UBSan通过，共45项。后者通过旧顺序反例重现错误fallback，新顺序验证嵌套事件及调参/完成期间停流不访问已释放buffer。模型不宣称所有硬件并发故障已测。

## 真机证据与适用范围

[r1](runtime-r1-validation.json) worker12693、[r2](runtime-r2-validation.json) worker13575，client/collector均终态。root分别`/var/lib/samurai/k421-history-r1`、`...r2`，原始payload/日志/报告保留，不能重复launch。

|验证|实际结果|
|---|---|
|r1候选四摄/双流/隔离IPA|四摄48+dual6+isolated27=81IPE；RAW-only六对不启IPE，六观测全部discard|
|r1观测边界|主摄10/12图像配对/提交，3份abort；发现上述重入问题，不冒充全配对|
|r2修复后主摄|12图像/12观测/12提交，无metadata-recovery fallback|
|r2隔离调参|29图像；28份有观测的应用曝光/增益与同SOF记录相符；其中1份成功乱序为superseded、27份commit；另1份未认领观测abort|
|r2真实缺统计|应用SOF7无BHIST观测，明确metadata-recovery，且无IPE_PAIR/token回执；不计为曝光/直方图匹配|
|正式恢复检查|r1/r2各前摄12帧；正式文件/驱动加载notes、个体配置均未改|

[r1逐帧核对](hardware-r1-validation.json)、[r2逐帧核对](hardware-r2-validation.json)逐token比较IPA→pipeline→最终回执的SOF/摘要，以及有统计帧的实际曝光/增益；prepared=commit+discard+superseded+abort，stop pending0。r1主摄缺陷的修正有实际代码变化，所以只复测主摄和隔离调参，没有重跑其它已通过物理摄像头/RAW用例。

r2第一次离线检查错误地要求每张成功图像都有BHIST，因SOF7 KeyError退出：[原检查失败记录](hardware-r2-first-check-validation.json)。随后只修检查器，将明确无统计且无历史提交的帧单列，没有修改原worker结果或为修报告再拍摄。不能把29帧说成29份有统计元数据的完整匹配。所有本轮原生IPA观测实际都在隔离进程；默认及强制隔离路径已测，在进程内路径仅有函数模型，没有宣称原生in-process IPA验收。

## 当前正式状态与下一步

[最终设备](current-state-validation.json)：正式419核心/适配器、libcamera r31/r26保持，kernel source419 `07d2ca735f88649587c0e89802febff6dbf2b443`干净；无模块卸载/刷写/重启。420模块epoch现239direct=原93+本轮146（r1候选81+r2候选41+正式重检24），失败/取消0，starts/stops17。资源释放、四设备suspended、17clocks0/9railsdisabled-users0，PW13618/WP13621 uid10000单例，owner_refs53为桌面句柄。guard394保持；本轮新fault/dump0，历史417 WARN taint512保留。

接下去把407..416的原厂数值模块、实际需要的LA/mask/weights/scalars/inverseGamma接入已验证输入/回执位置；确认IFE/IPE输入域，避免叠加已有CC/Gamma。完整TMC/LTM候选状态还需绑定其计算所依据的历史版本，处理重叠请求与失败依赖；观测类不能直接当作该数学时域状态已完成。缺统计需要明确的沿用/旁路策略，不伪造同帧数据。421候选未打包，后续匹配IPA2库/模块/代理统一集成，不能只替换一个文件。

[完整范围](../kernel363/REMAINING-CAMERA-SCOPE.md)保持：第五2MP身份及与前摄共享mux、多模式/帧长/防频闪、连续AF/光学/几何/多摄同步等仍需完成。原厂系数、完整日志和样本私存`/mnt/e/edk2-samurai-out/kernel421`及前序；公共仅作者代码及脱敏报告，本地镜像不push。
