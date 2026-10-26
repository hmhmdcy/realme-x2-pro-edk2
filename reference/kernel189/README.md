# 189：FastRPC冻结等待修复与连续三轮传感器休眠恢复

2026-10-15。完整外设goal active。仍kernel183/logdump183、boot/DTB172，新增同ABI的FastRPC模块候选；当前modules132中覆盖hci_uart185及fastrpc189两项，Mesa149/UCM173保持。当前SSC自动服务已重新启用，A.11在独立目录，原固件、系统libssc和APK数据库保留。

## 研究与实现

重新核对同SoC[Hotdog仓库](https://github.com/Sr-0w/hotdog-linux-bringup)，main仍为47087509c4289c2580c54f5433e55366b2e00445。其模组、电源域及SSC经验只作工程参考，不当作本机证明。[固定源码来源](related-device-source-reference.json)

Qualcomm作者的[FastRPC interrupted-invoke v3提案](https://lists.openwall.net/linux-kernel/2026/10/01/2547)解释了信号打断等待后，旧驱动重新分配context并重复发送RPC的缺陷。本机代码也没有恢复被打断context的路径。这与188的恢复后frpc_dsp fatal相符，但不是对本机异常PC的符号化根因证明。[固定邮件与补丁](fastrpc-proposal-reference.json)

没有直接套用未合入的v3：其说明与实际diff的sent/args处理有差异，当前本机源码也不能原样应用。189的[小补丁](fastrpc-freezer-wait.patch)使用内核现有`wait_for_completion_state(TASK_INTERRUPTIBLE | TASK_FREEZABLE)`，在freezer请求中保留原RPC及DMA缓冲；冻结竞态返回ERESTARTSYS时在同一调用内尝试冻结。普通信号的ERESTARTSYS及内核调用的10秒超时语义保持。没有修改SCM/VMID、DSP权限或旧186失败的共享池回收原型。

实际等待函数提取编译，52个场景覆盖0至15次冻结、真实信号退出、EPIPE、内核超时及poll降级；ASan/UBSan通过。删除冻结重试、吞掉普通信号、误把内核等待改为用户等待三个负例均编译成功后在运行时被检出。scheduler/freezer是主机stub，不能代替实机。[主机检查](freezer-host-validation.json)

ARM64目标模块W=1告警0，vermagic和全部导入符号通过，原183的12源及hci_qca185保持，Image/DTB/config未变，完整16793行Module.symvers及770项modules.order恢复。模块SHA88553112839d0a23604171edb03004a15e94f7cc3b174ebb3b9f2e56d3cc2fcc，源码SHA41c8db5c…。[构建](fastrpc-module-build-validation.json)

## 预检失败与部署

最初计划用pm_test=freezer隔离设备断电与用户线程冻结，但原#183没有CONFIG_PM_DEBUG或DYNAMIC_DEBUG。预检失败后，我错误地继续启动了SLPI试验；Python在读取不存在的pm_test前提时退出，**没有提交休眠**。原试验start0/query1/stop0，worker随后确认消失，现场及失败日志保留。不能将这次脚本失败当成原驱动的freezer复现；188完整PM失败仍是对照。

随后核对实际配置，改用不依赖这两个接口的完整RTC休眠对照。原fastrpc4515b1b2…完整备份，将候选原子放入默认路径；当前旧模块保留到热重启，未强制卸载。[模块暂存](module-staging-validation.json)。复用188已审查的RAM注册表/文件服务及OpenRC依赖，使用独立兼容库，旧boot因已用过SLPI拒绝再次start。[服务安装](auto-install-validation.json)

两次当前身份/分区/模块/资源排空/F2FS冻结门控的热重启，各只发一次RESTART2及fastboot reboot，无flash。第二轮nested私人目录导致首次fastboot核验工具找不到历史身份文件，在发送reboot前失败；修正路径、保留第一次观察，再重新观察同一fastboot身份/产品后才发送一次reboot，没有重复RESTART2。

第二新boot的候选模块文件SHA和实际加载build-id均匹配，SSC、SensorProxy自动启动，三种Has属性为1。严格启动核验被一条蓝牙UART错误拦下，检查确认FastRPC身份正确，错误实际为phase5、3.2Mbps、chunk13、partial0、firstff；与185处理的phase2前导00不同。该启动不标为全绿，只对已记录的这一条错误明确保留，继续传感器测试，其余所列启动错误0。[实际开机范围](candidate-reboot-runtime-validation.json)

## 连续三轮完整PM与桌面恢复

保持SSC、文件服务和SensorProxy持续运行，蓝牙关/未连接；每轮各只提交一次完整`s2idle`，RTC唤醒后再读取四种标准CLI流及D-Bus属性。

| 轮次 | 实际驻留秒 | 醒后accel/gyro/mag/light样本 | Wi-Fi关联观察 |
| --- | --- | --- | --- |
| 1 | 45.2784 | 46 / 46 / 9 / 10 | 约5.33秒回到5180MHz |
| 2 | 45.2053 | 46 / 46 / 9 / 10 | 35秒窗内未关联，保留为失败范围 |
| 3 | 45.2838 | 56 / 44 / 9 / 10 | 约0.53秒回到5180MHz |

三轮success增量3/fail0、RTC IRQ3、7266个PM callback end且err0；每轮八核trace overrun均0。四项CLI全部退出0/正常disable，原daemon及SensorProxy身份保持，无SLPI fatal、SCM、FastRPC、WARN/Oops/GPU/ASoC/蓝牙等所列故障增量。未做DSP重启或驱动重绑。[汇总](three-cycle-suspend-validation.json)、[首轮](persistent-suspend-validation.json)、[第二轮](persistent-suspend-r2-validation.json)、[第三轮](persistent-suspend-r3-validation.json)

**只证明这三轮传感器恢复，不能称整个网络/蓝牙/整机休眠完成**。第二轮Wi-Fi未恢复，第三轮经过了另一次PM，不能据此声称第二轮只是自行恢复得慢。

三轮之后，elogind核对的active本地Wayland会话UID10000再次Claim/Release加速度、光线、接近成功，原Polkit策略保持；普通CLI陀螺仪78、磁力计14、罗盘17条。LightLevel观测为8 lux，手机仍平放/方向undefined；没有人工亮暗、运动/方向或绝对精度验收。[醒后真实桌面客户端](desktop-after-pm-validation.json)

## 当前现场、回退与未完成

[828.17秒检查](final-validation.json)：三个DSP running、SSC及SensorProxy运行、A.11独立路径、传感器供电1、taint0；Phosh及Wi-Fi5180正常，蓝牙关/未连接。全boot保留蓝牙重组1，其它所列九项0。原厂来源分区/NV、303个来源文件及784项模块树通过；RAM副本复制前/后/副本三份哈希一致，私人归档SHA核对通过。[归档](evidence-export-validation.json)

原模块备份手机k189-module-deploy及主机E:/edk2-samurai-out/kernel189，原rootfs服务文件在k189-deploy。188原失败与回退均保留；189不把188改记通过。当前默认模块8855…与服务启用保留，实际运行版本已验证；不强制卸载被使用的FastRPC。维护内核现在tracked14（原13加本次fastrpc）。旧rootfs132更新会覆盖这些本地修复，仍需正式打包。

初次本地checkpatch的缩进/邮件头要求、构建包装器未完整替换旧输出路径、服务模板stage188标签和导出器overrun正则双重转义错误均保留并修正。初次构建被已有备份断言拦下、未编译；导出错误发生在完整归档已经下载/校验之后，修正后只解析现有材料，没有重复实机PM。

尚未解决：普通信号造成的通用RPC重试、freezer伪信号返回路径的严格审查、186共享池stop/start−22及SSR、跨boot/冷启动/长稳和人工传感器验收。当前三轮成功不能证明这些路径。继续高波特率蓝牙phase5错误和Wi-Fi PM恢复，并保留GPS UTC/aiding/真实fix/桌面桥、实体camera PM8008/CCI/C-PHY、蜂窝SIM/IPA与实际业务的完整目标。
