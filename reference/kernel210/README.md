# 210：前摄接入正常设备树并自动绑定，真实 RAW 取流通过

前摄不再依赖临时 overlay、VIO phandle 或性能辅助模块。已安装 IMX471、V4L2 CCI 库及支持地址迁移的 PM8008 模块，只更新 boot 中的设备树。新启动自动绑定 `imx471 7-0010` 和 `pm8008 1-0004`，media0 从22个内部实体变为23个实体，前摄正常进入 runtime suspend。[启动读回](runtime-validation.json)

## 源码与部署

修改前备份全部36份已有源改动、配置和产物。源码基线与实际204部署设备树均有910节点；以DTC YAML明确标记的引用归一化phandle后，语义完全相同，普通整数未被改写。新树925节点，仅新增15个前摄相关节点，并改变原CCI1状态和VIO phandle。[基线](baseline-semantic-validation.json)、[候选比较](camera-dtb-validation.json)

静态配置采用200实体取流证明的CCI1 master1/地址0x10、MCLK2 19.2MHz、四lane/200MHz及CSIPHY2。PM8008 Q复位是PM8150L GPIO4，未使用的P由GPIO1保持低电平复位；Q的NLDO输入引用S8C，前摄LDO2为1.050—1.056V、LDO5为2.8V，VIO静态引用PM8150L LDO1 1.8V。四路PLDO输入仍未知，没有虚构父电源。

首次候选被路径断言拦截：运行系统的i2c-1对应0x890000，源码标签实际为`&i2c4`，`&i2c1`对应0x884000。已修正后重新编译，错误候选从未部署。[板级补丁](persistent-front-camera.patch)、[配置片段](front-camera.config)、[源码记录](camera-source-validation.json)

常规配置已启用VIDEO_IMX471/V4L2_CCI/V4L2_CCI_I2C=m，五个开发helper均disabled。目标构建不再临时恢复配置；部分构建产生的符号表/删除的modules.order与原基线合并，保留16793个原符号并增加5个CCI导出，order为772。Image183及旧canonical DTB22c1保持；旧canonical不是当前部署树。[构建](camera-module-build-validation.json)、[最终源码](source-final-validation.json)

手机原模块树是770个ko/784份文件；部署后为772个ko/786份文件，仅三条模块路径变化，其余769模块逐文件保持，CAMSS与BT185保持。旧MFD及元数据在安装前已经导出私人回退归档；原生modprobe/卸载通过。[安装](module-install-validation.json)

新boot镜像89242ade…，内嵌DTB7ff712b1…，只改变UEFI中的FDT内容；其它固件、shim、header、ramdisk和分区尾保留。完整停用外设、归档并核对当前fastboot身份后，只刷boot一次，logdump/Image183未刷写。新boot读回boot/logdump/persist/NV与模块树均通过；回退boot为204 cdd16e29…。早期MM对象及BlueZ未就绪造成的两次观察失败已保留，未重复重启。[封装](build-package-validation.json)、[刷写](flash-validation.json)、[停用与归档](pre-reboot-validation.json)

## 真实取流与资源释放

WirePlumber自动发现新前摄并持有7个相机FD，传感器和CAMSS仍休眠。测试时确认唯一持有者是UID10000的空闲WirePlumber，短暂SIGSTOP，在finally中核对PID身份并SIGCONT恢复；未修改其持久配置。

首次硬件取流实际取得3帧且工具清理成功，但验收把VFE实际847000048Hz与请求847000000Hz做精确比较而停止。保留原记录后将检查限于100Hz取整差；另做两轮、每轮3帧，全部1928×1088 RAW10，每帧2628608字节，sensor/CSID测试图案均0，DMA缓冲区被图像数据覆盖、序号和时间戳递增。正式两轮共6帧，另有前次3帧，不能把前次失败的整轮验收算通过。

两轮都观察到VFE847000048Hz、CSID600MHz、MCLK19.2MHz，自身MMCX请求384；结束后自身请求0、MCLK关闭，传感器/CAMSS/CCI休眠，VDIG/VANA/VIO全部disabled/users0，原媒体图恢复。其它媒体FD为0的统计已排除暂时暂停的空闲WirePlumber；它最后已恢复。[两轮取流](static-front-capture-validation.json)

469秒独立健康再次确认前摄绑定和全部空闲资源状态；三个DSP running、taint及五类fault0，GPS0/Signals=false/rate30、BT关闭无连接，NV与产品程序保持。GNSS自动UTC准备在本次启动第8次尝试后完成，chrony Normal；没有手动时钟/轨道注入，也没有新开GPS收星会话。[最终健康](final-health-validation.json)

167份原生文件以一致快照导出，压缩包和每个常规成员均核对。原始场景RAW、私人标识和归档指纹不公开。[私人证据核对](evidence-export-validation.json)

## 用户态与下一步

root运行`cam --list`已枚举1个Internal front camera。仍有裁剪矩形EINVAL、静态属性/延迟/rotation提示，DMA buffer provider打开失败使软件debayer关闭，因此尚未验收完整拍照用户态。[检查](libcamera-inspection-validation.json)、[libcamera传感器接口要求](https://docs.libcamera.org/master/sensor_driver_requirements.html)、[内核DMA heap接口](https://docs.kernel.org/userspace-api/dma-buf-heaps.html)

源码已定位CROP分支赋值后break，最终落入-EINVAL；同时SYSTEM/CMA heap已配置为模块，需要下一阶段核对实际安装、加载、设备节点和权限，再修正启动接入。后续还要验证同一镜像第二次启动、完整冷启/未知PLDO输入、其它镜头和曝光色彩方向。

GNSS条件已由用户明确为室内窗边，不能排除弱天空信号，尚无无遮挡户外验收。209 UTC误差输入对照没有改善fix/CNR，候选未部署；不重复相同实验。[相关realme/OPPO/一加研究](../kernel205/GNSS-RELATED-DEVICES.md)。蜂窝真实业务、传感器精度/SSR、BT phase5、Wi-Fi/USB PM、完整充电和APK/rootfs整合仍属于完整goal。[当前检查点](../../NEXT-SESSION.md)
