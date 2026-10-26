# 290：原厂FULL后处理协议、公共驱动修复及完整部署

2026-10-19。290（2026-10-19）：#290完整Image/独立778模块已部署，原厂协议确认并修复VFE175 FULL后处理门控，带入TPG历史隔离和Gamma时钟修复。四摄RAW＋CPU ISP 235帧；标准接口TPG硬件NV12三帧、黑白中性通过，无用户态MMIO。实体硬件ISP/独立红蓝/统计与IPA/完整画质仍待做。

本轮按SoC/板级/驱动/用户态分层继续。原厂资料可参考，但开源内核不等于完整CamX/Chromatix算法开源；原厂DTS承载硬件事实，sensor/lens资料用于标准驱动协议，模组标定和图像算法进入匹配的IPA及数据包。[资料范围](../kernel276/OEM-TUNING.md)

## 原厂依据与硅上对照

固定CamX Chi参考9f17f1b568626b393e785b369c5dc94543774d7a的crop实现与本机HAL静态指令共同指向0x4c bit4。原来只打开CST bit0、MNDS bit3和单独Y/C round/clamp，FULL并未经过该后处理路径。仅增加全局门控后10→8位响应正确、clamp生效；不需要反转CST偏移字段、改矩阵、FULL client3/4或NV12 packer0xe。[固定来源](crop-reference-validation.json)、[HAL与硬件契约](full-route-contract-validation.json)

两次有界实验各15阶段93帧，先恢复Gamma表后控制CST常量和输出clamp；缺门控时512→0，补门控后512→128，128/256/1023分别变为32/64/255。恢复寄存器、原图及原inactive Gamma LUT192字逐字重读确认，资源回收无新增fault。[原响应](cst-response-capture-validation.json)、[正确路径](cst-route-capture-validation.json)、[临时像素对照](route-pixel-validation.json)。均为内部TPG，不证明实体画质。

生产修复位于camss-vfe-175-round.c，只在配置/停止FULL时读改写bit4，保留其它处理位。实际函数ASan/UBSan覆盖启停、无效参数零MMIO及旧路径隔离；checkpatch0 errors/0 warnings。提交15c8639d8badf5d4146bfd1b2c2fcb2460a137e5／samurai-full-route290，带入289两个修复，未推送。[主机验证](full-route-host-validation.json)、[提交阶段收据](full-route-commit-validation.json)。该收据not_deployed表示提交当时，实际部署由后续读回收据界定。

## 完整构建与单次部署

完整Image、DTB及778模块从同一提交构建，release7.3.0-rc6-rmx1931-samurai-k290+。39个CAMSS组件Werror，五阶段147.27秒、增量诊断0；BT三个模块先按新release构建再嵌入initramfs，与安装树完全匹配。depmod无未解析符号，CPIO/EFI FAT/Image/DTB与fsck核对通过。[完整构建](boot-candidate-build-validation.json)、[打包](boot-package-validation.json)

新release独立模块目录先安装并核778项，288及k132旧目录保留。正常停流、一次restart2进入bootloader，重新发现身份/分区后仅刷logdump、一次reboot；boot276/DT保持。新SSH端点/原hostkey及guard采用后，logdump/boot读回与778项匹配。[模块暂存](module-staging-validation.json)、[刷写](flash-validation.json)、[新启动读回](postboot-identity-validation.json)

首轮服务检查捕获尚未就绪阶段，之后服务自然启动，没有手动重启/修改配置；原失败保留私人日志，后续只读复核通过。[启动跟进](postboot-first-check-followup-validation.json)、[运行时](postboot-runtime-validation.json)。不能用旧rc.log历史失败代表本启动故障。

## 新驱动实际验收

四摄标准cam独立进程18段235帧通过，包含主摄SIGINT/重开，PM/rail/clock正常回收，无强杀或用户态服务重启。[四摄](four-camera-regression-validation.json)。日志确认普通相机仍Simple＋RAW＋CPU SoftwareIsp；imx471/imx319/s5k3m5缺专用调校文件，回退uncalibrated.yaml，主摄有s5kgw1.yaml但不是完整原厂调校。[实际路径及调校文件](regression-path-validation.json)

随后在最后主摄C-PHY历史下，标准MC/V4L2工具直接内部TPG→CSID175 IPP→VFE175 FULL，得到三帧320×240 NV12，图恢复，五sensor/lens保持休眠。工具不访问/dev/mem、不上传Gamma、不改路由寄存器、不预置D-PHY历史。[标准工具](standard-tpg-tool-validation.json)、[三帧实测](standard-tpg-validation.json)

第一帧与先前临时正确路径输出SHA完全相同：黑白Y0/255、U/V128，绿/品红响应正确。私人预览已核看。该TPG所有条纹R=B，仍需独立红蓝输入验证，不称完整色彩或实体硬件成像验收。[像素](standard-tpg-pixel-validation.json)

最终778项、旧288778项及旧k132776项、50用户载荷和961包核对通过；相机/CCI/CAMSS休眠、九rails/共享IO关闭、MCLK/CCI clocks0，fault0/taint0/pstore空，三DSP、SensorProxy、桌面、Wi-Fi/HCI保持。[最终健康](final-health-validation.json)。历史GPU与modem watchdog未因此结案。

## 仍需推进

实体sensor→硬件PIX、独立红蓝、统计/参数节点及帧级对应、libcamera硬件pipeline/IPA、模组校准与画质仍未完成。278单次Auto AF证据不晋升为290重测，Continuous/距离标定、GUI录像、旋转、第四后摄和长稳继续开放。当前仍有下游内核/关键包补丁及ignore_unused资源保留策略，不能保证无补丁更新；源码在树内不等于上游接受。目标保持active。

当前身份和回退见[检查点](../../NEXT-SESSION.md)。所有已执行部署/采集脚本先检查运行状态及产物再决定复用；私人像素、原厂二进制、校准、密钥未公开。289/288旧阶段记录和失败保留。
