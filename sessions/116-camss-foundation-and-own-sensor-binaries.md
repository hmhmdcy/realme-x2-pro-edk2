# 阶段116：CAMSS基础移植与本机摄像头二进制来源

2026-10-12。完整系统goal active。继承[阶段115](115-own-ipa-modem-and-zram-rootfs.md)无人值守要求，不做人工检查。手机保持第三次#115启动：USB SSH/F2FS rw、taint0、Wi-Fi、IPA、ModemManager(sim-missing)、zram；DPU CTL reset -22导致无DRM/Phosh/Phoc。没有在阶段116刷机或重启。

## 本机摄像头证据

本机vendor sda9以ro,noload,nosuid,nodev,noexec挂载，内核mount记录为norecovery；所有读取后卸载，完整分区hash保持、NV6通过。提取五个实际安装sensor.so：imx319、imx471、ov02a1b、s5kgw1、s5k3m5sx。readelf/objdump/strings保持私有，唯一共同导出GetSensorLibraryAPIs。反汇编显示API填入曝光/增益计算和寄存器写入回调地址；这些小型库没有足够的完整模组初始化描述，不把.so文件名当硬件实测。

初次在etc/camera查找sensor BIN无匹配，第二次扩大该目录深度仍无匹配；两次失败均已卸载/保留证据，未虚报提取成功。随后只读列出vendor metadata，确认BIN实际上位于lib64/camera。第三版按观察到的com.qti.sensormodule.*.bin路径提取六份：sunny_s5kgw1、qtech_s5kgw1、qtech_s5k3m5sx、sunny_imx471、qtech_imx319、sunny_imx319。没有复制tuned大文件、照片或EEPROM校准数据。OV02A1B有.so但该集合无对应sensormodule配置，不假定第五摄像头存在或已经接入。

六份BIN均有QTI Chromatix Header、Parameter Parser V1.3.2，offset28的小端长度与实际文件一致。完整归档606,128字节，SHA256 582eefb58aadd2709bb47f9570c353407a4cd20f1d8420e2a3472910eacb31e1，全成员SHA/分区hash/NV6核验通过。具体文件来源hash见reference/kernel115/camera-bin-source-validation.json；原始.so、BIN、disasm和strings均在E:/edk2-samurai-out/kernel115私有。还未建立带边界校验的register/power-sequence parser；不能用猜测偏移向硬件写寄存器。

## 隔离SM8150 CAMSS移植

参考[Hotdog公开源码仓库](https://github.com/Sr-0w/hotdog-linux-bringup)，固定commit47087509c4289c2580c54f5433e55366b2e00445，下载10个SoC/driver补丁和两份说明，所有文件有SHA。0055/0064提供SM8150基础与CSIPHY代际方案；0066/0067/0074/0075/0076涉及DMA/ICC/QoS/AXI，0089为C-PHY，0114为失败stream回收。只借SoC驱动方向，外国板级DT/传感器身份/固件不应用到本机。

/home/cy122/pmos-samurai-kernel116/{kernel,initramfs}从115独立复制，115的Image/源码保持。0055不能直接应用到7.3，原git apply --check失败已存档；语义移植四CSIPHY/两CSID/两VFE资源表与compatible。7.3移除了resources.link_entities字段，regulators变为regulator_bulk_data，按当前845表示形式保留supply/init_load。首次仅设置CAMSS被MEDIA_SUPPORT依赖过滤，修正媒体选项后首次编译暴露regulator结构错误，修正后对象编译通过。directory target只产生.o，不能把它误称.ko；之后完整Image/modules/DTB生成最终.ko并通过，所有失败日志保留。

自己的19781/sm8150-camera.dtsi明确qcom,csiphy-v1.1，加入CAMSS_8150独立版本，VFE行为沿用845，D-PHY lane选择参考v1.1(sc8280xp)表。这里只证明源码选择/构建；尚未完成本机逐项寄存器表比对、C-PHY、DMA/ICC/QoS，所以不能启用传感器或声称数据流已可用。

完整构建报告reference/kernel116/kernel-build-validation.json：Image SHA256 7ad5e8ffc60c2635649977d1100574574853708a4f6bc39090964a456554f275；qcom-camss.ko SHA256 4aa5928f3bee876a88b1a4f792a102cd1b292615ee08b9371dbf9a251e087ca1。DTB f3e970e5967c4f6768b3b8e2b54dad833a7a7f532eb6ae856093c3c1514877da与115逐字节相同，摄像头没有启用。IPA TX delay源码修正保留。未打包部署116、未修改当前启动套件；rootfs115 fixed镜像仍是最新已校验部署候选。

## 继续顺序

1. 本机BIN需先解析header/sections/type/长度并交叉核对HAL读取路径，确定slave地址、chip ID、reset/供电、MCLK、CSI lanes与mode寄存器。不能把Sunny/Qtech均安装当实际模组识别；需要安全自动probe证据。
2. CAMSS补齐本机SM8150资源DT（先禁用）、CSI PHY代际/CCI/CAMCC、DMA范围、ICC/QoS/AXI和C-PHY；逐项从自己的downstream证明，不批量套外国板级DT。完整build通过只是基础条件。
3. 显示CTL SW_RESET -22/RCU仍开放，沿115完整trace定位。可以准备有界阶段/寄存器日志候选，保留IOMMU前quiescence guard；不忽略timeout，不重复无变化重启。console慢打印只是待证实假设。
4. GNSS真实fix/桌面集成、充电、完整传感器、指纹、蜂窝数据/通话、休眠/长稳继续。维持15组状态，长错误记录后转项。

当前display/radio启动trace保存后off、PCM closed/双功放静音、SLPI offline/供电0，最后只读采集后taint0/zram/服务状态已再次保存。没有硬件强制reset、消息/呼叫、GPT/NV/persist写入、erase或全量userdata刷入。没有人工检查请求，没有公开固件/身份/原始日志，也没有运行旧自动push脚本。下一次重启/部署要使用当前115第三启动的新守卫与全排空/freeze，不能重放115首次或第二次守卫。
