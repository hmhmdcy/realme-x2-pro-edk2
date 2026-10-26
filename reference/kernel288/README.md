# 288：统一内核部署与首个硬件FULL NV12链路

2026-10-19。完整多摄及骁龙ISP目标继续。**新Image/778模块已整体部署，内部TPG→CSID175 IPP→VFE175处理→FULL NV12首次实际取得3帧；输出白/黑块偏色，硬件画质尚未正确，统计及libcamera硬件pipeline/IPA仍未接通。** 四个实体摄像头原有RAW＋CPU ISP路径在新内核上234帧回归通过。

## 当前实际部署

| 项目 | 已核对身份 |
| --- | --- |
| 内核源码 | `camera279-isp-kernel`／`samurai-vfe175-pix288`／`8c79b7e1912790d3e18a84c9c6621a6d92baa768`，本地提交，源码干净，未推送 |
| Image | build **#288**，release **7.3.0-rc6-rmx1931-samurai-k279candidate+**；59243008字节，SHA **6bad9512ac1481f864cb62f8da183761c240b01e7ece53f9f48026c9b55337f5** |
| logdump | 本次唯一刷写分区，67108864字节，SHA **8ec8b1e4d28ed76906ac9c9d31d8d791cab9d190c28d7f27224f8fb47e4aa56c** |
| 固件／DT | boot276保持，SHA **0d6bbc0255fc7a44340b2c2c6a20f2bfa807f683f69dd20a3fb130d961dc4c64**；DTB仍 **dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d** |
| 模块／用户态 | 新release独立目录778模块，原k132+的776模块保留；961包，libcamera r24/config-r19/PW-SPA-Gst1.6.9-r3保持，50个相机载荷逐项不变 |
| 新启动运输 | [host.py](host.py)，严格原主机密钥／新发现USB端点；新guard为手机`/var/lib/samurai/k288-work/boot-id-private.txt`，旧276启动ID已失效 |

[实际新启动/分区读回](postboot-identity-validation.json)、[最终模块/服务/PM](final-health-validation.json)、[当前部署锁](../../linux-port/camera/deployment-lock.json)。Phoc3564/Phosh3792、PW5163/WP5165，启动ticks及身份在手机k288-services-verified-private.json；续作重核。新I2C编号已变，按实体/driver查找：本轮GW1 8-0010、lens8-0072、tele6-002d、wide9-0010、front7-0010，不能复用旧编号。

## 现有方案与本轮分层

先重新读取[IFE测试工具](https://github.com/0xB0D/ife-tests)、[OPE工具](https://github.com/loicpoulain/camss-isp-m2m-test)及279固定的接口/源码；libcamera分支网页本轮访问失败，已有固定fda77c390源码继续可读。IFE测试采用标准media-controller/V4L2；OPE是另一处理引擎，未套用其寄存器。来源固定版本和哈希仍见[279](../kernel279/existing-solutions-validation.json)，本轮在自己的126标准TPG helper上适配，没有执行下载脚本。

| 层 | 实际变化 |
| --- | --- |
| CAMSS公共格式框架 | 可选独立PIX输出格式、输入/输出尺寸步长及无crop能力描述；未设置能力的旧平台保持旧行为。TRY与ACTIVE状态、格式枚举、capture布局和选择相互一致 |
| SM8150／VFE175后端 | 两个full IFE各保留RDI0…2，增加真实PIX行；16种8/10/12/14位Bayer输入，仅FULL NV12输出。单输出固定client3/4、group0；只注册sink/FULL两pad，未声明DS/统计/参数节点 |
| 尺寸与选择 | FULL16×4…4096×4096、宽步长16/高步长2；Bayer输入保持公共8191软件上限并对齐为8190，不声称硬件已验收该线宽。compose按能力调整，crop返回实际全compose区域，不偷偷执行ROI |
| 内核启动整合 | 从现机Image183校核启动/恢复脚本与认证，保留原initramfs，私有副本只更新三个内置BT模块到匹配新release；重建Image及全部模块，独立目录安装，单次进入bootloader/刷logdump/返回 |
| 板级／固件 | 无DTS、供电接线或固件代码改变，boot及DTB保持；没有增加测试GPIO或机型判断 |
| 用户空间 | libcamera/PipeWire/GStreamer/应用包未修改。硬件测试工具只用标准图/格式/控制及捕获接口；有界MMIO快照仅供开发诊断，在helper持流时只读，不成为应用接口 |

[完整补丁](vfe175-pix-candidate.patch)从287/6ddf1ba4c在独立index重建完整tree；七文件，checkpatch0 errors/0 warnings。[提交收据](pix-commit-validation.json)。前序Demux/MNDS、Gamma、CST、Demosaic和WB保持，本轮没有为首张测试图修改算法或原厂参数。[287来源与边界](../kernel287/README.md)

## 构建与启动闭环

[实际函数ASan/UBSan](pix-negotiation-host-validation.json)覆盖16种Bayer、524288组capture尺寸边界、格式枚举、真实descriptor初始化、TRY隔离、selection→capture→MNDS/DMA验证，以及旧平台/RDI行为；[处理模块回归](demux-mnds-host-tests-validation.json)继续通过。首轮测试包装器错误提取前置声明、mock缺字段而编译失败，修正后通过；首次checkpatch一处104列已修正，失败日志保留。

[编译候选](pix-full-build-validation.json)：39组件W=1/-Werror及完整Image/778ko，92.41秒，增量诊断0。该44MB产物没有initramfs，只能作为编译验证；部署检查识别后未刷它。旧全新构建1140条warning仍保留，增量0不覆盖历史。

[带启动输入的完整构建](boot-candidate-build-validation.json)：配置只改变initramfs源、默认UID/GID映射0和gzip压缩，当前config SHA **34204656424a03b7904c6d079aa0b112dafcec220b2a27b23c7b9afaa4eca8b2**。configure、Image/modules/DTB、modules_install三阶段均exit0，80.92秒／诊断0；778模块vermagic匹配，depmod未解析符号0。396项输入保留原属主/模式/链接，三个BT模块与安装树逐字匹配；认证/样片/二进制仅私存。

末尾配置检查器最初遗漏新出现的INITRAMFS_ROOT_UID/GID，发生在三个构建阶段已成功之后；补允许默认0映射，用独立finalize检查同一产物，没有重跑构建。先前产物六项已存私人completed-compile-pix288，287六项另存completed-demux-mnds287。

[打包核验](boot-package-validation.json)再次从真实新Image解出CPIO，验证启动/恢复脚本和三个模块，不只看.config；FAT中Image/DTB读回精确，fsck.fat只读通过。7,082,047字节模块归档SHA **7e8afa91b16ca655f6bb3f7021b695111253cd764d78b0f26c6242a0b14b2d85**，安全路径/778ko核对通过。[独立安装](module-staging-validation.json)采用64KiB校验块，旧776模块保持。

[25项音频/显示关键源码](preserved-source-validation.json)与Image183部署收据一致；这不是全部外设新内核回归。正常quiesce后[单次切换](quiesce-validation.json)、[fresh fastboot身份/几何](flash-validation.json)、[新boot读回](postboot-identity-validation.json)闭合；没有重发未知切换，未刷boot或其它分区。

## 硬件TPG：失败、定位和真实结果

1. r1 NV12格式/STREAMON成功，但0帧超时；停止后图和PM恢复，fault/taint0。[失败](tpg-r1-validation.json)
2. 同新内核RDI正对照取得3帧320×240 SGRBG10P，每帧96000字节全部覆盖、序号/时间递增，hash一致，正常回收。[RDI对照](rdi-control-validation.json)
3. r2用有界握手保持V4L2流，验证活跃时钟/资源后只读CSID/VFE寄存器，未用/dev/mem写算法。TPG寄存器实际为1920×1080/YUV DT0x1e，而IPP为RAW10 DT0x2b。[快照](tpg-r2-validation.json)
4. [原图](tpg-topology-validation.json)证实CameraManager留下RDI0启用链接；TPG按首个启用source格式生成数据。原测试工具仅断开物理输入，未隔离其它CSID输出。修工具先禁无关输出、最后启PIX，并逆序恢复全部改动；没有改驱动来掩盖错误测试拓扑。
5. r3 TPG实际320×240、DT0x2b、RAW10；硬件FULL取得3帧，每帧**115200字节＝Y76800＋UV38400**全部覆盖prefill，序号0/1/2、时间递增、hash一致。STREAMOFF/格式/控制/链接恢复完成，五sensor/lens休眠，九rails和时钟回收，fault/taint0。[实际NV12](tpg-r3-validation.json)

工具根据实体名和设备major/minor发现节点，发布前native/QEMU自测及错误kernel guard通过。r2/r3只读寄存器时C helper维持流并等待父进程令牌，避免PM后读掉电寄存器；DMI数据端口未读，未修改DMI状态。所有测试worker均已终态。

**出帧不等于正确成像。** [像素分析](tpg-pixel-analysis.json)证明不是单一填充值；NV12 SHA **bce327730e5b86c414393e31e9c3277c21f88ac63392902970874a60d7e9d788**。但与同设置的独立[RAW对照](raw-nv12-tpg-comparison.json)比较：RAW白块四CFA均1020、黑块均0；硬件白块UV为115/16、黑块236/234，明显偏离中性128/128。预览确实偏色，并有局部交替行差异，**颜色处理需要修复**。尚不能确定是Gamma/DMI、通道布局、去马赛克或输入域问题，不能用应用色彩补偿掩盖。

图像是内部合成TPG，不是手机实景；本地预览仅做标准BT.601 full NV12→RGB显示转换，没有CPU ISP参与生成捕获的NV12。RAW与NV12为两个独立合成会话，不冒称同request配对。真实物理bank/色序/位深尚未通过，标准Gamma64段sRGB模型误差约20个10位码值也仍在。

## 四摄与最终状态

[四实体摄像头18段234帧](four-camera-regression-validation.json)全部通过：17段各12帧，主摄SIGINT30帧，随后同镜头重开；无强杀或回归期服务重启。日志确认四路均为[Simple RAW→SoftwareIsp→ABGR8888](regression-path-validation.json)，不是误把新的PIX输出当作实体摄像头硬件ISP验收。新启动AF搜索、物理旋转、GUI和录像未重测。

[最终健康](final-health-validation.json)：778新模块与全部旧776模块核验，十模块加载note匹配，50相机载荷/961包保持；五sensor/lens、双CCI、CAMSS suspended，九rails/共享I/O OFF/users0，四MCLK/双CCI clocks0；全boot WARN/Oops/GPU/DSP fatal0、taint0/pstore空、CCI无错误。桌面/PW/WP正常，三DSP running、SensorProxy三Has真、Wi-Fi up、HCI存在。这不覆盖旧GPU默认负载、modem watchdog或长稳缺陷。

## 下一步及回退

先以合成黑/白/灰阶验证Gamma/DMI内容、使能、通道顺序与位深，再核CST/去马赛克；修到中性与已知输入响应正确后接实体摄像头硬件ISP。随后实现真实统计/参数节点、libcamera pipeline/IPA及帧级关联、模组标定/画质、四摄GUI录像和异常/PM。AF加速/Continuous/距离标定、Shine OV02A1B接入和完整rootfs复建继续，完整目标保持active，不承诺无补丁升级。

回退：保留boot276；原logdump183为67108864字节、SHA **e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358**，原k132+模块776项未改。私人kernel288/deployment-lock-private.json锁定镜像/回退，kernel248整机备份保持。没有执行实际回退往返。

当前输出仍/mnt/samurai-full282/build；必须先用284/storage.py核E盘backing并重挂。**config已变为带initramfs的34204656…，旧0c26bd91…构建脚本不可直接重放。** 输入位于同卷input-initramfs288，模块安装树modules288；均需挂载后访问，不能向空挂载点写入。raw编译Image abdebbef…未部署，实际使用6bad9512…。所有保存/打包/上传/切换/采集脚本已执行，不直接重放；继续前按实际句柄/进程与新boot guard核验。
