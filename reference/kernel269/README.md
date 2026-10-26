# 269：内核维护收敛、板级旋转修复与收尾

2026-10-18。用户要求沿主线 Linux＋SM8150 公共驱动＋RMX1931 板级描述继续适配，随后要求收尾、更新文档。本轮已停止新增实验；完整摄像头和整机适配仍未完成。

## 当前手机与已构建候选

| 范围 | 收尾状态 |
| --- | --- |
| 手机固件／Image | 仍为 boot267／Image183，`7.3.0-rc6-rmx1931-samurai-k132+`，773 模块、961 包；本轮没有刷写新内核 |
| 相机用户态 | libcamera 五组件 r19、config/stack r14、PipeWire/SPA/GStreamer 1.6.9-r3，49 项相机包载荷重新核对保持 |
| 当前启动身份 | 用户打开 Snapshot 后发生意外重启，原267/268 guard和PID失效；使用 [269运输代码](host.py) 和手机 `/var/lib/samurai/k269-work/boot-id-private.txt`，仍核原严格SSH主机密钥 |
| 当前桌面服务 | Phosh7908；PW8731/start75856、WP8738/start75860；手机 `k269-services-current-private.json` 为收尾权威，续作先重查 |
| 新内核候选 | 同一清洁提交完整构建 Image、设备树及773模块成功，release `7.3.0-rc6-rmx1931-samurai-k269+`，未部署 |
| 设备包候选 | samurai-platform 5-r1、samurai-desktop 3-r1 的配方及源校验通过，尚未构建／安装APK；对应两项手机配置已单独更新 |

## 内核收敛与验证边界

维护树 `/home/cy122/x2pro-linux/upstream` 的 `samurai-camera-common` 分支保留原 `samurai-bringup`。本地提交 d2ee8f275 删除五个已禁用的 OF 相机实验 helper 及其 Kconfig/Makefile 入口；1f5da50bbcba4fbe89917db7987429fdf078f257 把 RMX1931 固件 IOVA 保留区从公共 SM8150 描述移到板级设备树，公共 CAMSS 只检查完整平面是否满足 DMA mask、SG连续性和已映射长度。标准 IOMMU DMA 保留区路径继续负责地址窗口，不再在 C 驱动中重复机型数值策略；自定义 dma_trace 参数改为标准动态调试。

[清理](cleanup-validation.json)、[补丁](camera-dma-policy.patch)、[源锁](kernel-commit-validation.json)、[函数验证](dma-test-validation.json)。实际函数40024个ASan/UBSan案例及旧实现负对照通过；它不是内核 IOMMU 分配器或实机取流验证。

新旧设备树937节点及全部属性语义一致，CAMSS、PM8008、IMX319和reserved-memory四类schema零诊断。初次构建准备收据因schema文件名错误中止，后续审核复用了已完成输出，没有伪造成功或重放已完成构建。[准备与设备树](prepare-build-validation.json)。

完整 `W=1 Image modules DTB` 构建1833.35秒、modules_install 3.89秒，773模块与Image/DTB来自同一提交和配置，五个相机模块intree/vermagic一致；没有借用旧Module.symvers或vmlinux。**相机相关W=1诊断为0，全树记录1140条诊断，尚未逐条分类，不能称全树零告警。** [完整构建收据](full-build-validation.json)。

Image 59243008字节，SHA256 `9153da19b7ead38943792a84526723fb6d17177a0a2a45939972cd08465a3f61`；DTB SHA256 `51b289d64645a2decd77147a1d0be0ed2165ed3e72890086939da10a1e6e610a`。构建目录 `/home/cy122/x2pro-linux/camera269-full-build-r1`，状态已terminal/exit0，不要再次启动同一事务。initramfs输入的内容、所有者、模式和链接保持，含私人资料的镜像/输入和原日志仅保留本地。新内核及设备配置提交均未在本轮发布，完整rootfs尚未重建，现机仍使用267模块。

## 整屏旋转：板级配置，不改应用

用户确认正常竖握时原SSC Y约+9.7m/s²，SensorProxy误报bottom-up、桌面180°；原左侧边朝上时X约−9.7，误报right-up、桌面270°。补充标准矩阵 `-1,0,0;0,-1,0;0,0,1`，X/Y取反、Z保持。规则只归RMX1931设备包，供标准SensorProxy的SSC后端读取；Phosh、Snapshot、公共libssc源码不加入机型判断。[规则](99-realme-rmx1931-sensors.rules)、[手机安装](rotation-metadata-validation.json)、[平台配方](../../linux-port/packages/samurai-platform/README.md)。

**本次属于板级用户态硬件元数据，不能称为内核设备树修复。** 当前加速度计走SSC/DSP→libssc→SensorProxy，没有内核IIO节点读取／导出设备树安装矩阵。后续如接入标准IIO驱动，应通过设备树和标准IIO挂载矩阵接口表达机型安装差异；仅增加无人读取的DT属性不会生效。固件/libssc调试输出的矩阵并非正交矩阵，3D精度和原始placement解析另待审查，本轮只验证整屏方向。

矩阵安装后正常竖握连续10次normal；左侧朝上连续10次left-up，但当时桌面仍0°。GSettings锁旋转切换未解决，用户长按Portrait也无效；不能归因于用户操作。桌面启动早于SSC/SensorProxy，重建一次已就绪的桌面会话后，独立观察器未Claim传感器、未设置显示角度，连续120条记录为left-up／90°。用户随后明确反馈自动旋转正常。**观察窗口没有录下完整左右往返序列，因此完整序列的通过依据是用户反馈，不冒充机器采集。** [竖握](rotation-pose-normal-validation.json)、[左侧传感器](rotation-pose-left-up-validation.json)、[桌面观察](rotation-watch-validation.json)、[反馈边界](rotation-user-feedback-validation.json)。

桌面重建期间临时 `phosh --unlocked` 用户启动覆盖已恢复；没有改变原有lock/idle偏好，当前会话沿用--unlocked直到退出。[会话事务](ready-sensor-session-validation.json)。手机 `/etc/conf.d/greetd` 使用标准OpenRC `rc_need="dbus iio-sensor-proxy …"`，撤掉相反的before-radio边；依赖缓存更新成功。该配置已纳入 [samurai-desktop候选](../../linux-port/packages/samurai-desktop/README.md)，**下一次完整启动顺序仍待验证**。[启动依赖](sensor-startup-order-validation.json)。本地设备配置提交 `5e955a7c19355da6962eba9f03874cdf0081dfff`，两配方共25项校验通过，未发布／打包。[提交收据](device-config-commit-validation.json)。

## Snapshot意外重启：未解决

用户报告打开Camera (Snapshot)后卡死并重启。写入旋转规则之前，旧guard已拒绝执行；新启动读取证实规则当时不存在，不能归因为该规则。原始pstore console-ramoops-0共262132字节已保存私人目录，末尾约6196秒明确记录modem watchdog，约6202秒日志结束；未看到相机WARN/Oops调用栈，但日志截断和共同触发因素仍不能排除。[重启证据](unexpected-reboot-validation.json)。

重新核原主机密钥、机型、内核和五模块后建立独立269guard，未覆盖原267历史身份。新启动modem/SLPI/ADSP均running，modem/SLPI recovery原配置disabled保持，未触发SSR或重启测试。

只做了一轮既有Cairo启动器的Snapshot观察，36.84秒窗口未自然退出、没有新增内核fault；但两个sensor全程suspended，vb2完成／取出均0，**没有实际取流，不能算复现排除、相机验收或修复通过**。[启动探测](snapshot-startup-validation.json)。随后读取到显示进入息屏状态；标准ScreenSaver接口恢复亮屏后显示输出恢复。用户要求收尾，因此没有追加第二轮。现有GPU回退仍需要，Snapshot卡死重启与息屏/恢复下的相机行为需续作。

## 最后状态与续作

[最后只读健康](final-health-validation.json)：五模块加载note与磁盘匹配；四rails disabled/users0；双sensor、双CCI与CAMSS suspended；MCLK1/2关闭；961包、773模块、49项相机载荷保持；无相机进程，269跟踪关闭；本次启动warning/Oops/modem/fatal/GPU计数0、taint0。该健康值不抹除上一启动的modem watchdog。

下一阶段先核当前身份和用户操作后的状态，保存并分析旧pstore与应用/桌面日志；在确认实际出帧的条件下复现Snapshot故障。新内核部署前还需审核全树构建诊断及其它外设源码与现机的对应关系，准备一致的Image/DTB/模块/回退，再实机回归；本轮不部署。完整rootfs、公共用户态可重放整合、源发布、画质/低照度/相机图像方向、其它后摄、录像、GPU和长稳继续开放。用户延期纯色测试保持延期。

私人收据在 `E:/edk2-samurai-out/kernel269` 与手机 `/var/lib/samurai/k269-*`；原始场景、密钥、启动ID、USB端点和initramfs不进入公开文档。所有已执行的一次性目录保持终态；不要重放guard采用、元数据安装、会话重建、Snapshot启动或完整内核构建脚本。当前入口见 [NEXT-SESSION](../../NEXT-SESSION.md)，规则见 [WORKING-BOUNDARIES](../../WORKING-BOUNDARIES.md)。
