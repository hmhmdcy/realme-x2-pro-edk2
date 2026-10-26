# 267：公共 PM8008 供电、标准 IMX319 与新设备树实机启动

后续当前状态见[269收尾](../kernel269/README.md)：手机发生意外重启，当前启动身份与服务改用269；固件267/Image183及本阶段模块保持，新完整内核候选已构建但未部署。下文267/268的active、guard、PID与健康按历史解释。

2026-10-18。用户授权沿主线Linux＋SM8150公共支持＋RMX1931设备树路线收敛，并在手机验证。本阶段已经部署新DTB和三个公共模块，完整相机目标仍active；原生取流通过，跨进程切换的公共libcamera问题尚待修复。

后续[268](../kernel268/README.md)已修复该公共链路缓存问题并原生部署r19/r14，未改Snapshot的前后预览、界面切换、快门和JPEG解码通过，实测内核源也已同步维护分支。当前服务权威改为手机k268-services-current-private.json（PW16218/WP16224）；下文r15/r10和4314/4318为267阶段历史，boot267/Image183保持。

## 当前手机状态

boot267/Image183，仍7.3.0-rc6-rmx1931-samurai-k132+。**当前guard改为`/var/lib/samurai/k267-work/boot-id-private.txt`**；260旧guard与265旧PID不再代表当前启动。PC运输入口为本目录host.py，USB重新枚举后使用新鲜发现的IPv6端点及原主机密钥，私人端点不公开。[启动身份与分区读回](postboot-identity-validation.json)。

| 项目 | 当前部署 |
| --- | --- |
| boot | b79d0e0f53c9db04ca7b9de88727142eecdefed97229b8477226caf7ef6bf387 |
| PM8008 MFD | bcdbf711b1194a7eac46eaba626373bf9e82fdebd321e9a536e26d1c55076905 |
| 公共PM8008 regulator | d4dbb9cd7679381c97003c3bce901979d16c945e937d752dedc1fb75da3186d3 |
| IMX319 | 53917b9988e0796b4bc4724cd84932cf05882f4e9c81d4d3cbda9c11908a5cb5 |
| 其余 | IMX471 e49dab26、CAMSS ff9fdfa3保持；773个ko，961个包；libcamera r15/config-r10、公共PW/SPA/Gst r3保持 |

普通会话PW4314/start2484、WP4318/start2486，身份见手机`/var/lib/samurai/k267-services-current-private.json`。[服务核验](services-current-validation.json)。不再使用265手动服务清单。

## 已收敛的代码

- 两颗PM8008均由公共MFD与同一个上游regulator驱动扩展管理。删除独立IMX319 lab供电模块和板级reset-controller的部署文件及实验参数/softdep配置。GPIO编号仅留在DT；公共MFD按DT地址依赖暂时持有冲突PMIC复位GPIO，完成地址迁移后交还，并以标准device link排序消费者。不是单纯改名。
- 公共regulator仅注册DT明确描述的输出；电压由DT约束决定，增加READY等待及失败enable回滚。已证S8C输入在两颗PMIC的NLDO供电中描述；未知PLDO来源不编造，省略输入不创建dummy supplier。仍不能据此声称完整电气原理图已确认。极端I2C清理失败仍可能留下不确定输出，模型明确保留该结果，未做实机故障注入。
- IMX319改为`sony,imx319`，删除机型判断、lab child查找及固定供电电压；用CSI endpoint的链路频率选择传感器配置，寄存器表保留。方向仅来自DT；Selection API返回既有模式的模拟裁剪范围，未知rotation未填写。
- 新DTB仅删除专用复位节点并改变八项已列明属性，其余语义不变。[源核验](source-validation.json)、[DTB](board-build-validation.json)、[绑定](binding-validation.json)。标准接口不等于本地扩展已合入上游。

三模块真实树内W=1无诊断，intree/ABI/导入符号通过，canonical源码和构建目标恢复。[构建](module-build-validation.json)。传感器370个故障案例、地址30例、公共enable24例、地址冲突32例、supplier link8例及负向对照通过ASan/UBSan；这些是API结果模型，不是内核并发或硬件故障注入。

## 启动与实机结果

第一版固件重建被检查器拒绝：三个非相机模块仅Git版本字符串改变。限定构建时的原固件版本后，第二版逐模块证明只有内嵌FDT改变，36条既有诊断、无新模板；固件代码、Image183、logdump、shim/ramdisk/header/尾保持。[固件版本](firmware-version-validation.json)、[启动包](build-package-validation.json)。

三个模块暂存、删除两个实验模块和一个loader配置；其余模块及包库保持，暂存期间加载中的旧模块不热卸。[事务](module-transaction-validation.json)。PC与手机均保存20个原文件；PC归档415305字节、SHA256 92071138211f90406d81f1a5cf547d4138f42e04dc52d24c373432f79dce9e44。[回退](rollback-validation.json)。

完成当前启动的硬件quiesce后，只发一次restart2到bootloader，fresh fastboot原身份/几何核对后只刷boot一次；已启动Linux并完整读回新boot摘要，logdump/NV/校准未刷。[切换](flash-validation.json)。

实际两颗PMIC、两sensor均绑定，三个加载note等于磁盘新模块；后摄方向Back、crop(0,8,3280,2448)，四路电源OFF/users0，实验模块/参数/节点均不在运行。[启动硬件](postboot-hardware-validation.json)。标准cam直接枚举前后摄，无应用私有路径或复制开关。

未改动的cam以普通用户环境完成前后各三轮、每轮12帧，共72帧；每轮真实序号0—11递增，关闭后PM休眠、四rails OFF/users0、MCLK1/2关，新增WARN/Oops/GPU/fatal零、taint0。[原生开关](native-cam-validation.json)。全局既有CPU ISP配置保留，尚非GPU路径验收。

GStreamer run16因诊断目录权限在启动测试脚本前失败，无取流。修正诊断目录后run18遇到真实跨进程链路冲突：标准cam最后用前摄后，长期运行的PipeWire/libcamera按缓存认为前摄链路未启用，未发送禁用动作，后摄link setup返回EBUSY。现场电源已回收，内核无新增fault；失败和日志保留，不把它记为拍照通过。

已核对公共SimpleCameraData::setupLinks源码：对冲突链接的disable和目标链接的enable均依赖缓存的ENABLED位；跨进程改变MC图后可跳过必需ioctl。下一步修公共libcamera逻辑并实机交替验证，不外部写media图或重启服务掩盖问题。当前相机库尚未因本阶段改变。

后摄低照度/颜色、GUI切换与快门、其它后摄、录像、默认GPU及完整kernel/rootfs源码整合仍开放。私人场景与原始系统日志不公开，阶段资料在`E:/edk2-samurai-out/kernel267`及手机k267目录。一发式暂存、quiesce、restart和flash均已执行，不可重复重放。
