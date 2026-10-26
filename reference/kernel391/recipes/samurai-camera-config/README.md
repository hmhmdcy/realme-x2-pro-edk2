391当前：libcamera r30/config-stack r25已正式安装，默认IPE四摄／RAW／隔离IPA及普通用户PipeWire共94新增作业通过，个体配置未打入公共包；完整IQ与多摄校准继续。[391证据](../../../../reference/kernel391/README.md)。以下为历史。

360候选：libcamera r28／config r23已完整构建和签名检查，尚未安装。包含349 Gamma与359原厂曝光程序，启用私有Gamma配置需348参数ABI；公共默认YAML不变。原r27／r22配方仍为已安装版本。[360记录](../../../../reference/kernel360/README.md)。以下为历史。

342当前：r27/config-r22已部署，CAMSS338保持。已合入个体WB/CCT、实时lux驱动CCM及动态LSC；四摄安装后显式配置通过，默认YAML无个体表。实际模式曝光表选择及正常光学校准继续。[342证据](../../../../reference/kernel342/README.md)。以下为历史。

321当前：r26/config-r21已部署，318 CAMSS保持。LSC的IPA合成、模式重采样及启动参数上传完成，真实内部图案链路通过；默认个体LSC尚未启用。四摄取流及安装后GStreamer／PipeWire通过，正式光学与多摄校准仍在继续。[321证据](../../../../reference/kernel321/README.md)。以下为历史。

316当前：r25/config-r20与314 CAMSS已部署，默认选择硬件管线。四摄GStreamer NV12、主1080p／前720p、四摄RAW和安装后PipeWire NV12通过；315的双流／AE／AWB／单次AF证据沿用。完整画质校准、多摄同步与连续AF未完成。[316证据](../../../../reference/kernel316/README.md)。以下为历史。

278当前：r24/config-r19已部署通用单次AF、帧携带清晰度统计与串号回执的标准镜头控制，原生触发/取消/重触发/停流及自动曝光下AF通过。模组行程/搜索参数仅在设备数据包。配对测试单次AF约9–12秒，仍需加速；连续AF、距离标定、完整画质、GUI/录像和Spectra未完成。[278证据](../../../../reference/kernel278/README.md)。以下按历史阶段阅读。

277当前：r23/config-r18已部署通用RAW空间清晰度统计和标准FocusFoM，主摄同请求RAW重算与元数据逐帧一致，失焦与恢复对照通过；保留完整功能。AF搜索/距离标定、GUI/录像和Spectra仍未完成。[实际部署](../../../../reference/kernel277/README.md)。以下按历史阶段阅读。

276当前部署：libcamera r22/config-r17，新增通用 Simple 镜头流生命周期；CameraManager常驻枚举四摄后镜头fd释放，供电/时钟回收。标准V4L2手动对焦已有光学响应，四摄238帧回归通过；AF算法、画质、GUI/录像、Spectra及r22完整手动曝光矩阵仍待验收。[现机证据](../../../../reference/kernel276/README.md)。以下为历史阶段。

273已部署：libcamera r21/config-r16 新增 GW1 原生增益 helper。主摄 RAW/RGB 与600帧CPU JPEG已出帧，四 sensor 238帧交替通过；高分辨率手动切换测试仍失败，AF/画质/GUI/Spectra未完成。[部署及失败范围](../../../../reference/kernel273/README.md)。以下为历史阶段。

271（2026-10-18）：当前原生部署libcamera r20/config-r15，新增标准S5K3M5原生gain code/32 helper，配套内核控件32…512。481码factory测试、96组物理细分增益、三摄193帧与600帧普通预览通过；初始AE慢、画质/AF/GUI/主摄/ISP仍开放。必须和新sensor模块配套更新或回退。[271](../../../../reference/kernel271/README.md)、[当前源锁](source-lock.json)。下列r19及更早叙述按历史解释。

# Realme X2 Pro 相机配置包

当前config/stack为0.1.0-r14，固定五个libcamera组件为99990.7.2-r19。三个配置载荷内容保持，仅升级依赖版本；49项运行载荷、961包及其余954包记录核对通过。相机接线和供电已在公共内核驱动/设备树管理，不添加发行版私有供电脚本。[268部署、应用验证和回退](../../../../reference/kernel268/README.md)、[当前输入锁](source-lock.json)。以下r10/r15为历史。

当前config/stack为0.1.0-r10，固定libcamera/IPA/tools/gstreamer/v4l2为99990.7.2-r15。配置payload保持CPU ISP/system heap、heap模块自动加载与权限，目录0755/文件0644。通用堆video/uaccess，FastRPC池root0600。[239记录](../../../../reference/kernel239/README.md)、[源锁](source-lock.json)。

16MP默认关闭，须模块参数和用户态Quad双实验开关；产品YAML保持。r15已核系统默认取流、两次start初始参数和WirePlumber新库加载；普通/隔离IPA的完整控制矩阵是225历史验收。后摄光学/颜色和全零帧仍待处理。

r15→r13/config-r8回退使用225实际七包及239事务前world/repo/配置，保持当前ff9/e49等内核模块；降级模拟通过，未完整往返。本包不含内核、设备树或私钥。
