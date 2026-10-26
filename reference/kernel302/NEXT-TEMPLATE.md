# Realme X2 Pro 当前检查点

2026-10-19：[302硬件IPA控制与有效帧上下文](reference/kernel302/README.md)。SensorHelper／DelayedControls已接入候选，当前IMX319模式960帧及36次控制变化通过；AE／AWB、多摄／多模式、个体标定和完整IQ未完成，目标继续。

## 当前部署与启动身份

实际手机仍 **#298／7.3.0-rc6-rmx1931-samurai-k298+**，内核树`/home/cy122/x2pro-linux/camera279-isp-kernel`，samurai-blc298／c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117。Image、778独立模块、boot276、DT与原厂固件未变。产品libcamera0.7.2-r24／config-r19、PW／SPA／Gst1.6.9-r3仍走RAW＋CPU ISP；候选只在私人目录，未安装。

Image SHA eb8054e69991528cad4f126d7723b7ef4869b288fb85c992f4803cbfeab5ddaf；logdump dfef7be4f358c5c16e8e716a60c24da8a139de73b1e07912d70f2b58613d80df；boot 0d6bbc0255fc7a44340b2c2c6a20f2bfa807f683f69dd20a3fb130d961dc4c64；DTB dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d。

302/host.py保留原SSH密钥与严格 **`/var/lib/samurai/k298-work/boot-id-private.txt`** guard。本轮无刷写／重启，旧启动身份不用于当前切换。按entity发现，当前main8-0010／lens8-0072、tele6-002d、wide9-0010、front7-0010；生产代码不固定CCI编号。[部署锁](linux-port/camera/deployment-lock.json)、[源码锁](linux-port/camera/kernel/source-lock.json)

## 已验证与当前缺陷

- SoC仍为298的VFE175 WB／BLS、图像／参数／Y BHIST共享SOF；BLS scale为Q11 unity，范围伸展在用户空间显式表达。没有新增内核／DT／UAPI或通用helper补丁。维护内核仍为本地树，未证明上游接受。[298](reference/kernel298/README.md)
- 299原厂Sunny IMX319全部16个IFE BLS模式／288区域均960 U14，经两种解码核对；原厂参考不是SensorBlackLevels或本机暗场。EEPROM两读各12287字节一致，完整布局／校验仍未核实，未应用个体数据。WB2.22／1.90是临时场景值；用户暂不遮光。[299](reference/kernel299/README.md)
- 300标准IPA／IPC及真实DSO56字节协议已接通，修复重复init线程归属和测试媒体图恢复顺序；旧失败及一次单链接恢复保留，勿重放恢复脚本。[300](reference/kernel300/README.md)
- 301先测9个控制阶跃均SOF＋2响应。302按模式时钟配置接入现有CameraSensorHelper／DelayedControls，转换标准曝光／模拟增益并回报实际量化值及Manual模式。立即保存每个SOF的控制快照供异步统计使用，失去连续性／读回不符则使上下文失效。当前配置只用于IMX3191632×1224、209066666 pixel/s、2080行长、3350最小帧长。[302实现](reference/kernel302/README.md)
- 最终R3隔离／R4签名线程各两轮240帧，共960图像／统计／有效曝光增益及Mode元数据、36次控制变化。BHIST与144个NV12 Y分区响应对齐；真实写入均SOF＋2，手机8文件哈希核对。隔离请求有时多延后一图像帧；元数据按实际有效值，不能假定发起request即生效帧。[独立实测](reference/kernel302/runtime-association-validation.json)
- 最终图／控制读回恢复，5传感器／镜头、两CCI与CAMSS休眠，9供电关闭／用户0，taint0、匹配worker全退出，新增四类故障计数0；资源约1.3秒自然休眠。961包／50相机载荷／778模块全量检查与桌面服务PID沿用300最后记录，本轮不扩大为重跑证明。[300全量](reference/kernel300/final-health-validation.json)
- 仍未实现硬件AE／AWB、动态WB／BLS参数、多摄／多模式和完整IQ。Y BHIST不提供RGB AWB；晚启统计、严重IRQ延迟、丢SOF、取消／worker故障和长时间控制队列回绕未完整验收。GPU默认故障、旧modem watchdog、SSC偶发EPERM未关闭，whole_system_healthy=false。

## 源码回退与下一步

SDK `/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline` **现为302源码**，使用reference/kernel302/build-candidate.py，勿重放299／300源码安装器覆盖。最终包302/ipa-bundle-r2-private.tar.gz，SHA a12020406954ba8663d92a53155445a8b04c532172392e428be9f109baa66c94；补Mode前R1包和源保留，不能混计最终Mode接口通过。所有R1—R4终态，勿盲目重放采集。

已测300源码保存在私人301/tested300-source-private.tar.gz，SHA26b68040fb01fc91b82f5583905a08c8fefe52e9dc70970ae5b7486599551fa7；300最终包SHA84fcad6db75979b2f88f0350118aec83025f8536d2206aadd2e77efbdeec5206保留。

接下来复用libipa AgcMeanLuminance，以当前模式线性BHIST和有效曝光／增益上下文接硬件AE；补颜色统计与AWB、其它摄像头和模式、EEPROM布局／校验、正式暗场／色彩／阴影调校。S5K3M5 crop bounds／静态属性缺口继续下沉驱动处理。

内核构建输出/mnt/samurai-full282/build，先用284/storage.py核backing挂载并保留Rust环境。稳定回退仍#290 logdump SHA0f169a331d1c4aac98cd67f636c9f30dd0c727ffc20a6031e4de142d7f57396a及独立778模块；297等旧产物、k132776／248备份保留。55提交／177文件的内核派生、产品28个libcamera配方补丁／6个PW项目补丁和ignore_unused尚未证明跨版本零补丁升级。[层级审计](reference/kernel298/layering-validation.json)

私人根E:/edk2-samurai-out/kernel302（300／301保留），个体数据／场景／密钥不公开。[操作边界](WORKING-BOUNDARIES.md)
