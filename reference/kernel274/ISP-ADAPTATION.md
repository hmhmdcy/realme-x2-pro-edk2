# SM8150 / VFE17x ISP 适配分层

280纠正：本机原厂SM8150描述选择VFE175/CSID175；本页170寄存器/20 client属于此前参考检查，不能据通用驱动符号认定实际硅型号。后续按175/24 client推进。[280证据](../kernel280/README.md)

后续279已固定现有IFE/OPE/libcamera方案并完成公共框架独立候选的ARM64对象编译和参数边界修复；未部署，VFE170硬件PIX仍未接通。[279当前证据](../kernel279/README.md)。以下保留274源码检查边界。

2026-10-18。此页是源代码定位和实现边界，**没有声称新增 Spectra 成像功能**。[固定源码证据](isp-gap-validation.json)

当前维护基线 3184c56（本轮 lens 候选没有改变 CAMSS）与本机原厂内核提交 9668fcdc6ec15be7a10d66f7b93c347829e0fdb6 的 VFE170 资料已经交叉读取。原厂 cam_vfe170.h 定义 20 个 bus client、18 个输出；CAMIF、lens/stats/color/zoom 模块控制以及 FULL、DS4、DS16、FD、RAW_DUMP 与统计输出确实存在。它证明硬件接口线索存在，不证明当前 Linux 已驱动这些模块。

维护源 `camss-vfe-17x.c` 的 writer 使用 MIPI RAW 模式及 RDI stride。`camss-vfe.c` 的 `vfe_formats_pix_845` 标注 TODO，并引用 `formats_rdi_845`；因此 VFE 的 pix 命名及资源表中的 formats_pix 不能作为硬件颜色处理证明。现机真实路径是 CSIPHY/CSID/VFE RDI → RAW buffer → libcamera Simple CPU ISP。

| 层 | 应实现的内容 | 不能混入的内容 |
| --- | --- | --- |
| SoC 公共驱动 | VFE170 CAMIF/PIX 模块、输出和统计 DMA、IRQ、reset、带宽/电源及错误恢复 | RMX1931 模组曝光值、镜头供应商、场景/应用判断 |
| 板级 DT | 真实 clocks/power domains/CSI 连接、电源、GPIO、内存约束及 lens phandle | AE/AWB、去马赛克、降噪/锐化策略 |
| 内核公共接口 | 可审查的 V4L2 media/request、参数与统计接口，格式/大小/生命周期校验 | 无约束任意寄存器写接口或 Android HAL ABI 包装 |
| libcamera pipeline / IPA | 驱动硬件处理管线、逐帧参数/统计对应，AE/AWB/AF 和错误恢复 | 将 CPU/GPU 软件去马赛克的输出误记为 Spectra |
| 设备调校数据包 | 对应 sensor/镜头/模组的黑电平、颜色、阴影、噪声和对焦标定 | 在通用驱动硬编码原厂风格、场景或本机默认焦点 |

后续实现需要从实际源代码/寄存器定义建立受控硬件配置及统计路径，再补匹配 IPA，并在标准用户入口验证输出。原厂内核主要提供资源、bus/top/IRQ/命令执行和模块接口，不能据此推断公开仓库包含全部 IQ 算法。原厂 CamX/Chromatix 二进制不能直接作为 Simple tuning 文件加载。

验收必须包括真实硬件处理后的像素、对应 request 的参数/统计、四摄切换/异常退出、资源回收与 PM；输出格式枚举、寄存器写成功或构建成功都不能独立证明 ISP 已适配。GPU ISP 已知故障与旧 modem watchdog 继续独立保留。
