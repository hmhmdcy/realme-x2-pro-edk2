# 296：VFE175 统计 SRAM 初始化与首包修复

2026-10-19。当前实机 **#296 / 7.3.0-rc6-rmx1931-samurai-k296+**，干净源码 `samurai-stats296` / `f86906688666c0ebaabaeeec96c28d5741257f50`。完整 Image、独立778模块及加载模块 build-id 已核对。boot276、DTB、固件、961个包和50个相机载荷保持。多摄/骁龙ISP目标仍 active；本轮修复统计首包，BLC、IPA、产品硬件pipeline和完整画质继续推进。

## 改动落在哪一层

修复仅在 **SM8150/VFE175 SoC驱动** `camss-vfe-175-stats.c`，一个本地提交、37增/1删。寄存器复位后，BHIST计数SRAM需要初始化：在输入像素到来前临时打开BHIST SRAM时钟，通过DMI清零1024个计数槽，再恢复共享DMI配置、地址和原时钟门控策略。沿用既有标准队列与typed CAMSS ABI，板级DT、固件、UAPI和产品用户态包均未修改。[补丁](bhist-init-candidate.patch)、[源码收据](source-validation.json)

没有丢弃首包，也没有用户空间MMIO写入或CPU伪造直方图。物理测试程序已把首包计数设为强制条件；错误会报错退出并正常清理，不能再通过只检查稳定帧掩盖首包异常。

## 原厂与现有仓库依据

GitHub代码搜索找到了此前缺失的生成寄存器头 `titan170_ife.h`。两个仓库固定版本含同一blob `bd94210d738d3a3b947231a16f33e03601cbf33a`，文件SHA256 `800a9dbbf2bdf16ec36a03bd670d733bee8f63d4d9ed0311de9b24e29413cf53`：

- [固定参考一](https://github.com/Hozzu/TFLite-aarch64-linux-with-delegate/blob/b60c3300678c6d7102810d30414e296c0b2335ce/onboard/home/pkshin/include/camx/titan170_ife.h)
- [固定参考二](https://github.com/comprehensive9/vendor_qcom_proprietary/blob/36fc163a534963a5b3af52186af5efcc63401ad2/prebuilt_HY11/target/product/kona/obj/include/camx/titan17x/titan170_ife.h)

它定义DMI配置/地址/低数据寄存器0xc24/0xc28/0xc30、BHIST RAM选择0x3a、BHIST时钟与使能bit4。此前固定Camx初始化流程会清零1024项BHIST RAM。结合[295真实首包失败](../kernel295/statistics-pixel-validation.json)，本轮把初始化补到SoC驱动。[仅数值协议与来源哈希](dmi-protocol-sources.json)

完整参考头保存在私人目录，未复制原厂实现，也未执行厂商二进制、套用其它手机调校或触及工厂校准。两个仓库是相同文件的拷贝，不是两个独立硬件规格。

## 实机验证

| 场景 | 实际结果 |
| --- | --- |
| 长焦首次运行 | S5K3M5 GRBG10、2104×1560图案2，真实CSI→CSID0→VFE175 FULL；99图像/90统计。初始首包820560、图像关闭/重开后的首包820560、统计晚启动首包820560均精确匹配；全幅/半幅/最小ROI稳定帧820560/410280/2正确。[首轮](statistics-pixel-validation.json) |
| 广角实景 | IMX319 RGGB10、1632×1224，传感器和CSID图案关闭；18图像/18统计，含第一个包，人口全部499392，无无效包。[实景统计](optical-statistics-validation.json) |
| 广角切回长焦 | 再做99图像/90统计；首次和图像重开首包正确。随后关闭统计流，重开参数流将ROI改为4×2，再晚启动统计，首包和稳定帧精确为2；未出现旧全幅计数。[第二轮](statistics-r2-pixel-validation.json) |
| 合计与负对照 | 216图像/198统计、7个启动/重开/晚启动首包检查全部通过。全部记录的人口落在相应已知ROI集合，广角18包人口全部精确。295启动与重开的反例保留。[汇总与范围](startup-fix-validation.json) |
| WB回归 | 首轮11阶段颜色误差<1.235，10非法包、7参数完成；五次可观察颜色变化首帧与PARAM_DQ一致。第二轮新增停统计时重开参数流，共8次参数完成。[颜色](stats-pixel-validation.json)、[有限帧号证明](frame-association-validation.json) |
| 曝光与预览 | 曝光500→3000→500：Y75.0741→93.3138→75.0732，稳定统计均值bin71.9740→113.7148→71.9721。已查看私人图像，结构可辨，仍暗绿，BLC/AWB/IQ未校准。[图像](optical-pixel-validation.json)、[复查](optical-review.json) |
| 原产品四摄路径 | libcamera RAW＋CPU ISP 18段244帧通过，主摄SIGINT40帧后重开12帧正常；不等于主/前摄硬件ISP路径通过。[回归](four-camera-regression-validation.json) |

主机侧：真实旧函数不满足SRAM初始化合约；新函数清零全部1024槽，检查时钟/选择/模式/显式地址及共享状态恢复，ASan/UBSan、10万ROI案例、metadata启停、图像重启与部分启动失败回收均通过。[负对照](parent-init-validation.json)、[实际函数测试](stats-host-validation.json)、[回收回归](fixed-restart-metadata-validation.json)

当前证明范围为上述两传感器/两模式/320×240 FULL、一轮实际启动。严格图像—统计SOF关联、队列饥饿/合并IRQ、多参数Request API、其它模式与长稳仍需验证；因此 `ready_for_automatic_exposure=false` 保留。统计首包修复通过，不能据此声称IPA、BLC或完整硬件ISP用户态已完成。

## 当前部署、资源与后续

完整构建153.08秒、五阶段诊断0、40个CAMSS组件严格编译通过；778模块vermagic/depmod一致，3个嵌入BT模块与安装树一致。[构建](boot-candidate-build-validation.json)、[封装](boot-package-validation.json)、[启动读回](postboot-identity-validation.json)

最终相机/镜头/CCI/CAMSS均suspended，9路供电及共享IO关闭，MCLK/CCI时钟0；fault0/taint0/pstore空。桌面、SSC、SensorProxy默认成功，Wi-Fi/HCI与modem/adsp/slpi正常，未重试SSC或临时nodeps恢复。#293偶发SSC EPERM根因、GPU默认路径故障、旧modem watchdog及整机长稳未结案；`checked_runtime_healthy=true` 仅覆盖所列检查，`whole_system_healthy=false`。[最终检查](final-health-validation.json)

Image SHA `f226c1739061fd0f228f6efde9d05a6c55943c1296184723931eefdc9077ecc6`；logdump `64616e8fd6e4327e6a07d5c738bea7b7707922703f8a69a97f11ec11af08605e`；config `82e39f7ea2ad2507417290cfbcd5754dd3f4ee431bb3a73b31e8f880e5e04233`。本轮一次正常切换，仅刷logdump，boot276与DTB保持。295六产物在私人kernel296/completed-boot295，旧独立模块树保留；稳定回退仍首选#290镜像及原778模块，未做回退往返。

后续优先统计与图像SOF关联、BLC和libcamera硬件pipeline/IPA，再补主/前摄硬件路径、模组调校、AF Continuous/距离映射、Shine OV02A1B、GUI录像和长稳。原厂DT提接线、驱动/HAL提协议、IPA承载算法及匹配本机模组的数据；不硬编码单场景黑电平。

项目仍为主线7.3rc6派生树，53本地提交/177改动文件；libcamera配方28补丁（含发行版既有）、PipeWire另6项目补丁，三个ignore_unused仍在。已有底层修复，但尚不能承诺升级零/最小补丁，跨版本、完整rootfs和上游接受均未证明。[分层与更新依赖](layering-validation.json)、[295分层详述](../kernel295/README.md)

维护树 `/home/cy122/x2pro-linux/camera279-isp-kernel`；输出 `/mnt/samurai-full282/build`，先用284/storage.py核backing并挂载，input-initramfs296/modules296。运输用本目录host.py及 `/var/lib/samurai/k296-work/boot-id-private.txt`，按driver/entity发现总线节点。构建、切换及全部采集已终态，勿盲目重放；私人像素、参考载荷和密钥不进入公共文档。
