# 当前检查点：387（四摄 libcamera → IPE，82帧通过，目标active）

先读WORKING-BOUNDARIES.md、reference/kernel387/README.md。386完整交接归档archive/NEXT-SESSION-through386-2026-10-21.md，早期固件／DMA／失败审计继续保留。用户已关灯睡觉，黑／噪点不单独判故障，照明校准后做，不阻塞底层适配。目标没有完成、暂停或blocked。

## 当前源、设备与边界

WSL Ubuntu root；源码／构建前调用reference/kernel284/storage.py::mounted_build()，持久ext4挂载/mnt/samurai-full282，绝不格式化或重建32GiB backing。主内核源source354，HEAD8003933b7e31e4b5f4d27d21789d42da686831ba，branch samurai-ipe-pipeline387，干净；父386ab58f554a7b9f886bd43b9c3f47d52761d9bf982，中间5bd45e8aecb4e978de7400073678abca77bc376a。

内核只改m2m媒体稳定driver_name=qcom-ipe-a5和独立cancelled诊断计数。SoC核心／条带／IQ／回收保持386，核心二进制b429dc7b37fb22d9a5628a90eb3e27b780e4df3da568750f815ac7ae09a3b56d。实际构建产物private387 *-intree-r2.ko；adapter115544B/a7fd24755c2aaa667a1591fdd44778aa6dd0d69fcc61213589bff40ca6604546，helper/test与386相同。build-intree.py构建四个运行模块及四个vb2目标供modpost，W1/Werror无诊断，共享输出/config/symvers恢复，不替换现有vb2。

libcamera候选/mnt/samurai-full282/libcamera387-ipe-built/src/libcamera-v0.7.2，基于安装r29对应的libcamera362-serialized-built；final patch reference/kernel387/camss-ipe-pipeline.patch，camss_ipe.cpp/h和camss-vfe-after.cpp为最终源。common pipeline_handler.cpp、IPA/src/ipa/camss-vfe/camss.cpp未改，保留362同步隔离IPA重入修复。最终库SHA60181b3cd025febfeb1812996bc63aaa53721a47ba45bd6ef1d3f92596329c3d。

设备仍378恢复boot，host387委托386→…→378，guard /var/lib/samurai/k378-recovered/boot-id-private.txt，原371→360 USBkey/known_hosts。安装Image363、boot366嵌DT365，libcamera五包r29/config-stack r24和362四个私有Preview不变；静态ICPdisabled/仅SID2222，未刷写、重启或永久安装387。SSC旧attach EPERM/daemon exit4、SLPI offline问题未修，别盲目重试DSP或声称全平台健康。

## 实际管线

acquireMediaDevice以driver qcom-ipe-a5和entity qcom-ipe-a5-source发现m2m；媒体节点/sys/bus/media/devices，动态video/media编号。内部IFE缓冲→m2m OUTPUT、应用DMA-BUF→CAPTURE，现有V4L2VideoDevice处理连续颜色平面合并。核心仍CPU拷贝到自有DMA，非零拷贝；没有用户空间像素处理。

先双端S_FMT再任何REQBUFS；输入共享FD包装以保存IFE原始SOF／timestamp。输入、输出均DQ后才完成request并回收内部IFE；RAW配对仍用原始IFE。请求关联在应用回调前移除。RAW-only不运行IPE；没有endpoint才走旧IFE，有endpoint失败会报错。m2m当前固定1:1 NV12/NV21、端口8/max_cores2/RT、IQ旁路，不能冒称缩放或完整高级IQ。

本版libcamera字符串构造V4L2M2MDevice未连video watchdog槽，CamssIpe自有3秒timer。STREAMOFF失败后close joins work再归还剩余缓冲，该对象拒绝重开以免旧queuedBuffers记录被复用。正常stop/start可重用；真实错误会failed计数，ECANCELED单列cancelled，错误处理和DMA retain条件未放宽。18个实际源码ASAN/UBSAN provider用例通过，但硬件异常／全并发不因此获证。

## r5 实机与失败审计

唯一成功/var/lib/samurai/k387-pipeline-r5，worker21629，client/collector/worker终态。四摄GStreamer各12帧NV12/640×480；主摄RAW+NV12六请求、原始SensorTimestamp相等、六组SOF最大15885ns；RAW-only六请求／SOF最大23854ns，IPE0；隔离主摄28帧、五控制阶段、GammaACK1，统计PID不同于应用。合计jobs82/completed82/cancelled0/failed0，FWstarts6。最终FW单handle create/destroy/peak1、28帧MAP/UNMAP、messages91/IRQ92/debug1/wd0/proto0，正常PC/WFI。r5没有测试实际取消分支；不要把模型或旧r3混合计数当作物理取消证明。

前四次均回收且服务恢复：r1用model匹配driver，IPE0却12帧IFE，拒绝假通过；r2两队列format/allocation顺序EBUSY，IPE0；r3四摄输出各12，旧failed1具体ret未记录，不能事后确定ECANCELED；r4四摄与RAW两个模式通过，私有库被判未安装，隔离IPA找不到proxy。最终env LIBCAMERA_IPA_MODULE_PATH=/usr/lib/libcamera/ipa、LIBCAMERA_IPA_PROXY_PATH=/usr/libexec/libcamera，只通过LD_LIBRARY_PATH私有覆盖core；签名IPA/proxy/base沿用安装r29。旧collector10s窗口在r3超时，无dump／fault；r5为330s且逐用例查活跃，正常19.262s停止。

current-state验证五次进程均不活跃、无临时modules/video/media/FW、taint0、CAMSS/双CCI suspended、9rails disabled/users0、17clocks0，PW21706/WP21712恢复。进程ID只作本轮证据，后续看实际状态。真实82帧核心数据证明依赖386既有像素／UV误差，本轮核对帧完成／hash／元数据，没有再做全图identity。现场亮度不作门槛。

## 接续

推进SG/DMABUF直接DMA去复制，正式平台owner及板级启用；补显式在途取消／错误并发，接原厂Gamma/LTM/CCM完整IQ／模式与完整剩余校准。第五2MP身份、动态帧时长／防频闪、几何和多摄同步、连续AF仍待。不要缩小成只完成管线或只四个传感器；reference/kernel363/REMAINING-CAMERA-SCOPE.md为全部范围。

继续保留381七SID/DMA retain与reset ACK回收、373 reset后HFI参数、375 PC/WFI、376严格token/ACK、379 MAP/UNMAP wire长度、377/378失败审计；383 Unicorn全局MEM_READ hook破坏Thumb IT/SP，离线只能用已验证有界hook并比较完整CDM/job。384原生条带及385多模式/386m2m完整证据继续有效。原FW/HAL/汇编/CDM/完整日志/图像/个体校准仅private，公开镜像/home/cy122/edk2-samurai/repo的Platform/Realme/sm8150作用域本地提交，不push/PR，保留其它改动。
