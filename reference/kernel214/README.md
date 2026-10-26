# 214：完整相机包已部署，默认客户端通过

本轮把213的隔离修复整合进完整libcamera软件包，已在同一启动升级并验收普通用户默认取流，没有刷机或重启。范围是前摄1928×1088 RAW10/CPU ISP、首帧修复和软件包集成；完整16MP、图像质量、后置四摄、GPU ISP及其它外设仍未完成。

USB重新发现邻居后恢复同一scoped端点，用原密钥确认同一启动。213原归档按64KiB续传，全部227成员核对通过；此前截断/超时保留，不声称根因或大传输稳定性已修。[连接](fresh-endpoint-probe-validation.json)、[回收](previous-evidence-recovery-validation.json)。214新鲜基线确认原r4三包/数据库/配置保持，保存48份文件记录，三个DSP running、相机休眠、taint/五fault0。[基线](baseline-validation.json)。

独立宿主Alpine/aarch64构建root使用QEMU10.2.1、ARM GCC15.2.0和4个编译任务。完整r5配方保留原auto/virtual、全部子包、六个补丁及tuning/desktop输入，加入IMX471 helper、1µm属性和CPU首帧LUT三补丁。0010仅增加可选外部IPA密钥构建项，默认空值保留上游行为；strip后用同一保留密钥重签IPA，APK沿用203项目密钥。[配方与源锁](../../linux-port/packages/libcamera/README.md)、[构建](full-libcamera-build-validation.json)、[特性](full-feature-configuration-validation.json)。

11个相机子包及2个设备配置/栈包全部构建，13包按手机现有信任验签；34个ELF均aarch64、5个IPA及签名齐全，无私钥/运行脚本/文件归属冲突。宿主ARM模拟下cam/lc-compliance/qcam帮助、Python导入和全部5个IPA对编译核心内嵌公钥验签通过；没有把这些检查当作手机画质验收。[产物](forward-package-artifact-validation.json)、[运行检查](host-runtime-qa-validation.json)。保留源码、工具和私有签名输入，但未重复构建验证二进制逐字一致。

回退依据来自实际安装r4的备份文件和包数据库：3个快照包保留原内容、模式、软链接和依赖，使用现有受信任项目密钥签名，明确不冒称原发行版签名。缓存r4原包签名无法用保留信任验证，故未采用。用手机实际940包记录在宿主完成真实升级/回退，49条前向记录及44条原包记录核对通过，937个无关包记录不变，配置和world恢复。[回退输入](rollback-snapshot-inputs-validation.json)、[快照包](rollback-snapshot-package-validation.json)、[完整演练](package-roundtrip-validation.json)。

完整候选实机先通过暗场RAW、CSID数字白RAW与RGB，再通过手机原生安装预演。随后一次记录状态的APK事务升级libcamera/IPA/tools三包至99990.7.2-r5，新增gstreamer/v4l2/config/stack四包，当前944包；49条安装文件记录核对通过，原3份配置被包管理接管。相机栈固定版本，本地索引也已验签。仅重启原本空闲且加载旧库的WirePlumber，PipeWire和桌面进程身份保持，新进程加载r5库且没有旧删除映射。[候选](full-candidate-staging-validation.json)、[预检](native-install-preflight-validation.json)、[安装](package-install-validation.json)、[用户策略进程](wireplumber-reload-validation.json)。

安装后的UID10000使用系统默认库与CPU配置，没有loader/IPA候选路径覆盖。6帧物理暗场RAW均值63.9844～63.9881、标准差0.4411～0.4423，相邻帧33.03%～33.14%像素变化，非全零或冻结；读前后DMA同步并排除行填充。暗场RGB首帧14～15，黑位校正后其余5帧为0，这本身不判bug。CSID全1已知输入的6帧RAW每像素1023，6帧RGB从首帧起每字节254，未丢弃首帧。[暗场RAW](system-dark-raw-validation.json)、[暗场RGB](system-dark-rgb-validation.json)、[白RAW](system-white-raw-validation.json)、[白RGB](system-white-rgb-validation.json)。传感器内部TPG仍未作为有效正对照。

默认cam和安装的GStreamer插件通过标准API各取6帧，无报错、超时或新增内核fault。手机未装gst-inspect/gst-launch工具，首次检查因此停止；随后编译有限无窗口appsink客户端验证插件，不新增工具包。未用未同步的GStreamer缓存像素作画质证据，也未保存/展示房间场景。[客户端](default-clients-validation.json)。

最终sensor/CAMSS/CCI suspended，前摄两电源disabled/users0、MCLK与自身MMCX票释放、图案关闭；3DSP running、taint/五fault0，NV及非相机程序核对保持。GPS0/Signalsfalse/rate30、UTC第8次准备成功、chrony Normal，蓝牙关闭无连接。[最终健康](final-health-validation.json)、[源码](source-final-validation.json)。本轮私人原生归档167成员与完整归档均核对通过，不含私钥和场景图。[归档](final-evidence-validation.json)。

保留的失败：首次构建校验和顺序错误、第二次缺libyuv运行库均在输入/配置阶段终止并已修；配置包索引最初因宿主缺项目公钥失败，加入现有公钥后验签通过。宿主首次回退索引命令误用了mkndx不支持的--compat，改为deflate压缩；候选首次预检误按完整版本匹配SONAME，实际0.7软链接正确，已在采集前修正并保留原记录。以上失败不改写成通过。[校验顺序](checksum-order-repair-validation.json)、[libyuv](libyuv-dependency-repair-validation.json)、[配置构建](config-package-build-validation.json)。

回退须先重新核对当前启动、安装状态及相机/音频空闲，使用/var/lib/samurai/k214-package-candidates/rollback的3个签名r4快照。先删除samurai-camera-stack（本机原生模拟只会移除4个新增包），再通过仅含rollback/packages.adb的临时repositories文件明确安装三个=99990.7.2-r4；随后从k214-baseline/files恢复原3份配置和world，核对原库记录、移除本轮60-samurai-camera.list并重载WirePlumber。不能只还原库而留下r5包记录，不能忽略配置包删除时也会删其文件；快照重签后的APK数据库不声称与原数据库逐字一致。实际回退未发送。[当前回退检查](installed-rollback-readiness-validation.json)。

续作：IMX471内部TPG的0600/0601位宽、延迟/曝光/tuning/方向、完整16MP和应用画质；后置四路逐路供电/时钟/CCI接入；GPU ISP另修CMA/全黑/IOMMU释放。GNSS真实fix/正CNR、蜂窝真实业务、BT phase5、传感器FastRPC/SSR、Wi-Fi/USB PM、充电闭环、其它硬件及radio/Mesa/完整rootfs均保持开放。[全硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。
