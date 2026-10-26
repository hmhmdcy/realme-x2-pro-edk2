# Realme X2 Pro 当前检查点

2026-10-19：[300硬件IPA与生命周期](reference/kernel300/README.md)。IMX319手动硬件IPA候选两执行模式通过；完整多摄校准、逐帧控制、AE／AWB和完整IQ未完成，目标继续。

## 当前部署与启动身份

实际设备仍 **#298／7.3.0-rc6-rmx1931-samurai-k298+**；内核树 `/home/cy122/x2pro-linux/camera279-isp-kernel`，干净samurai-blc298／c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117。完整Image与778独立模块已部署，boot276、DTB、原厂固件保持。961包／50相机载荷未变，产品为libcamera0.7.2-r24／config-r19、PW／SPA／Gst1.6.9-r3，仍走RAW＋CPU ISP。

Image SHA eb8054e69991528cad4f126d7723b7ef4869b288fb85c992f4803cbfeab5ddaf；logdump dfef7be4f358c5c16e8e716a60c24da8a139de73b1e07912d70f2b58613d80df；boot 0d6bbc0255fc7a44340b2c2c6a20f2bfa807f683f69dd20a3fb130d961dc4c64；DTB dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d。

300/host.py沿用严格原SSH密钥和 **`/var/lib/samurai/k298-work/boot-id-private.txt`**，本轮未刷写／重启。按entity发现，当前main8-0010／lens8-0072、tele6-002d、wide9-0010、front7-0010；不要把CCI编号固定进公共代码。Phoc3789／Phosh4029／PW5436／WP5438保持，start_ticks见[最终健康检查](reference/kernel300/final-health-validation.json)。旧启动guard不用于当前切换。[部署锁](linux-port/camera/deployment-lock.json)、[源码锁](linux-port/camera/kernel/source-lock.json)

## 已验证与当前缺陷

- SoC沿用298：公共WB等通道减偏移U16→U14 BLS，scale保持Q11 unity；拒绝不等减偏移／非零加偏移，停流旁路恢复。图像／参数／Y BHIST按CAMIF SOF关联。驱动仍是本地维护树，详见[298协议与范围](reference/kernel298/README.md)。本轮不加DT／UAPI／内核补丁。
- 299原厂Sunny IMX319 BLS全部16模式／288区域均960 U14、阈值0，原厂解析器与独立解码一致；显式参考减偏移3840及范围伸展已作硬件对照。本机EEPROM双读各12287字节一致；完整布局与原厂校验未知，未应用个体数据，未写EEPROM。WB2.22／1.90是临时场景估计，非正式调校。用户暂不遮光。[299数据边界](reference/kernel299/README.md)
- 300将调校解析、编码和统计检查移入标准IPA／生成代理／worker；handler负责MC、三队列、epoch／原始SOF／租约。真实DSO56字节包逐字节参考、无效统计／重复序号／旧epoch、重开与回绕契约通过。默认签名线程R4和独立进程R5各三轮24帧，共144图像／统计／SOF／逻辑ColourGains元数据核对；每代理只init一次，资源约1.3秒自然休眠。[独立实测](reference/kernel300/runtime-association-validation.json)、[契约](reference/kernel300/ipa-contract-validation.json)
- 当前只是IMX3191632×1224→320×240、启动手动WB／BLS的**候选**，未替换产品库。逐请求控制仍拒绝；sensor helper／DelayedControls、实测延迟、AE／AWB、多摄／多模式和完整画质未完成。Y BHIST不是RGB AWB，statistics_ready_for_automatic_exposure=false。用户空间R3断言已修，失败／图恢复保留；严重IRQ延迟／取消／worker故障未完整验收。
- 最终5传感器／镜头、两CCI及CAMSS休眠，9供电和共享IO关闭／用户0，MCLK／CCI时钟0，fault／taint／pstore／CCI错误0。桌面／SensorProxy、Wi-Fi／HCI与三个DSP维持。GPU默认故障、旧modem watchdog、SSC偶发EPERM根因未关闭，whole_system_healthy=false；GUI录像／物理旋转／本启动AF未重测。四摄产品回归沿用298的18段233帧结果，本轮未重跑。

## 源码回退与下一步

SDK **`/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline`现为300源码**，不要重放299构建脚本覆盖。用reference/kernel300/build-candidate.py；新模块接口／源码／证据均在300。299已测源码归档及R2包保存在私人根，旧包SHA4519b7009383e815e9073256a3bc5a1592abf484d1b28c7859a5b7e492974ba4；300最终包为ipa-bundle-r4，R4／R5使用同包。

R2发现隔离变量按存在性生效，默认须移除；R3默认重开重复init触发线程归属断言，修为一次init＋configure/start、release销毁代理。旧fixture恢复输入顺序冲突留一条链接，已按保存图通过标准MC恢复并读回相同；新fixture先禁用再启用。[恢复](reference/kernel300/graph-recovery-validation.json) R1—R5均终态，无匹配活worker；勿盲目重放采集或恢复脚本。

接下来验证晚启动统计、逐帧参数、取消／worker故障和丢失SOF；复用sensor helper／DelayedControls实测曝光／增益延迟，再接AE与有效颜色统计／AWB，扩多摄和模式、完成EEPROM校验与模组调校。S5K3M5 crop bounds／静态属性缺口待底层收敛。原厂BLS不是SensorBlackLevels，不把正常场景拟合当暗场标定。

内核／模块构建产物和config哈希见298；输出/mnt/samurai-full282/build，先用284/storage.py核backing挂载并保持Rust环境。稳定回退仍#290 logdump SHA0f169a331d1c4aac98cd67f636c9f30dd0c727ffc20a6031e4de142d7f57396a及独立778模块；297／296等旧产物、k132776和248备份保留。

维护内核为7.3rc6派生55提交／177文件，libcamera产品配方28补丁含发行版既有，PW6项目补丁，三个ignore_unused仍在；无上游接受／跨版本迁移证明，不能承诺零补丁升级。[原产品更新审计](reference/kernel298/layering-validation.json)

私人根E:/edk2-samurai-out/kernel300（299／298保留），像素／个体校准／密钥不公开。[操作边界](WORKING-BOUNDARIES.md)
