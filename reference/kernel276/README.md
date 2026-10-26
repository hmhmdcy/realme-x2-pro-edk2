# 276：公共 CCI 供电收敛、标准手动对焦和多摄回归

2026-10-18。完整目标继续 active：多个摄像头及骁龙 ISP，按 SoC、板级、公共驱动、用户空间分层收敛。**三后摄加前摄可取流，主摄标准手动对焦已产生光学响应；AF 算法、画质、GUI/录像和 Spectra 成像仍未完成。**

## 当前实际部署

boot276/Image183，`7.3.0-rc6-rmx1931-samurai-k132+`，776模块/961包；libcamera五组件 `99990.7.2-r22`、config/stack `0.1.0-r17`，PipeWire/SPA/Gst仍 `1.6.9-r3`。boot SHA `0d6bbc0255fc7a44340b2c2c6a20f2bfa807f683f69dd20a3fb130d961dc4c64`；DTB `dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d`。Image、logdump、固件可执行部分保持，此次固件仅DTB变化。[构建](build-package-validation.json)、[实际读回](postboot-identity-validation.json)

维护树 `/home/cy122/x2pro-linux/camera270-kernel` 分支 `samurai-cci-io276`，干净提交 `0d69276125ec8e7d0cc083ac421e2ad7fe79a3c8`，父提交0798ee688为标准镜头适配；原3184c56分支保留。未推送。**源码在维护树内不表示已被 Linux 上游接收。** Image183没有整体重编，269完整候选未部署，最新完整统一内核/rootfs仍待构建验收。

## 分层和底层修复

| 层 | 本次实际内容 |
| --- | --- |
| SoC | 原有 CCI 的 TITAN_TOP_GDSC 正确，未新增或修改 SoC dtsi |
| 板级 | cci0/cci1 各增加 `vddio-supply` 指向共享1.8V I/O；无其它DT节点/属性变化；镜头沿用275标准 phandle/VAF归属 |
| 公共总线驱动 | `i2c-qcom-cci` 管理可选 vddio，在时钟/传输前申请、空闲释放；按拥有的引用处理回滚/重试，移除时只在恢复成功后访问 halt 寄存器 |
| 镜头驱动 | `onnn,lc898219xi` 标准 V4L2 focus/runtime PM，VAF唯一消费者，不硬编码本机场景或默认208焦点 |
| 用户空间 | 275部署的Simple通用镜头流生命周期；常驻枚举释放镜头，流期间标准打开，停止释放 |

公共CCI驱动没有镜头型号、地址或机型分支。该修复使独立 lens 操作不再依赖另一 sensor 偷带共享供电；板级描述负责声明真实连接。[补丁](cci-io-candidate.patch)、[供电源码](i2c-qcom-cci.c)、[DT精确差异与三组schema](board-validation.json)

Image183兼容模块 W=1 构建零诊断；从实际 PM/remove 回调编译的14个主机用例覆盖供电/时钟失败、引用回滚、重试和移除，UBSan通过，实机没有注入电源故障。C文件checkpatch零error/warning。[模块](current-module-build-validation.json)、[主机用例](cci-power-callback-validation.json)

新CCI模块 SHA `b2808f63c0e290a7aa5808de687d2001b8f936595a8632d2a1055b05aa8ca42b`，镜头模块 `03517eeac1b88820cfa24a0932ce5832e9f47260793cc703b64228c487cd5f1d`；替换CCI时其余775模块逐字节保持。十个相机相关模块实际加载 build-note 与磁盘匹配。libcamera七包49载荷复核通过。[最终健康](final-health-validation.json)

## 实机验证

- 所有 sensor suspended 时，标准 lens 子设备独立打开及枚举 focus_absolute 成功；未再出现275的CCI超时。瞬时状态曾为suspending，后续稳定检查均suspended。[独立打开](lens-initial-validation.json)
- 真正存活的 CameraManager 枚举四摄，无 lens 初始化错误，未持有镜头fd；四sensor、lens、双CCI和CAMSS均休眠，九相机rails及共享I/O OFF/users0，四MCLK与双CCI时钟计数0。正常停止后保持。[生命周期](manager-lifetime-validation.json)
- 主摄真实 RAW12/RGB12 通过；RGB序号有一次跳帧，不声称每帧必达或已验证30fps。[取流](main-capture-validation.json)
- 原生 libcamerasrc 流期间实际持有镜头fd，VAF恰一消费者；通过标准 v4l2-ctl 设208/304/880/208，每阶段六份统计和一张私人JPEG，无原始I2C旁路。880明显失焦，返回208可见细节恢复；边缘扩散代理约9.4/8.04/46/8.88px。[标准控制](standard-focus-validation.json)、[离线光学分析](standard-focus-optical-analysis.json)
- 前摄/主摄/广角/长焦18段238帧交替通过，包含主摄SIGINT正常退出与重开；未强杀，回归期间桌面与PW/WP未重启。[四摄](four-camera-regression-validation.json)

V4L2 GET为缓存目标，不是硬件位置反馈；自动曝光未锁定，JPEG和统计不是同一request，指标用于证明光学响应，**不证明最佳焦点、距离标定或自动对焦**。中央平墙ROI容易受噪声影响，不能仅按其梯度分数验收AF。样片仅本地私存。

最终相机设备/电源/时钟回收，taint0、fault0、pstore空且CCI错误列表为空。SSC、SensorProxy、greetd在275/276两次默认启动正常，三DSP运行，SensorProxy报告加速度/环境光/接近传感器存在；没有nodeps恢复。**物理旋转未重测，旧boot273 EPERM根因未证明修复。** GPU默认故障与Cairo CPU回退、旧modem watchdog仍开放。

## 失败、回退与下一步

保留275独立镜头CCI超时及两个供电对照；276首次暂存因`/lib/modules`与`/usr/lib/modules`路径别名断言失败，发生于备份/变更之前，r2改为解析真实路径后成功。首次停服务提交使用旧273guard，被拒于worker创建及停服务之前；检查终态后更新为实际275guard，原失败记录保留。没有未知切换结果下重复发送重启。275与276两次受控切换均终态成功。

276匹配回退为实际boot275和旧CCI，手机/PC双份24228955字节，SHA `a12acbdf518011cc6685f6e4be725893311b79e0188d965434fec94feeb3a5b2`；包维持r22。275另存boot273/r21/r16完整相机回退。未执行回退往返。[276回退](rollback-validation.json)、[275回退](../kernel275/rollback-validation.json)

续作使用 [host.py](host.py) 和 `/var/lib/samurai/k276-work/boot-id-private.txt`，先核当前身份；USB接口与子设备编号可能变化，按实体名称查找，不重放已终态采集。私人资料 `E:/edk2-samurai-out/kernel276`。已归档旧273部署锁/r21配方，再提升实际r22/r17配方和276部署锁。[提升核验](source-promotion-validation.json)

下一步完成标准libcamera AF控制/算法与模组校准，重测r22完整手动曝光矩阵、四摄GUI/录像及物理旋转。273严格手动矩阵失败、274同矩阵两次通过均保留，不能据未复现宣称根因修复。第四枚物理后摄仍未确认。Spectra仍是CSIPHY/CSID/VFE RDI RAW→Simple CPU ISP，硬件PIX成像/统计、公共参数接口、pipeline/IPA仍需实现。[ISP边界](../kernel274/ISP-ADAPTATION.md)、[原厂资料怎么用](OEM-TUNING.md)
