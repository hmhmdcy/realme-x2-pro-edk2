320更新：[本机HAL分组规则](../kernel320/README.md)已解释此前4个零节点：每51点需额外跳过1字节，修正解码后均非零；没有补造或写回数据。原文中的零节点结论为当时错误候选布局的历史记录。

# 318：VFE175 镜头阴影网格已验证并部署

2026-10-20。已安装318 CAMSS；仍使用298 Image、305 S5K3M5、libcamera r25及config/stack r20。新增可选LSC参数块，默认关闭；真实模组阴影表尚未启用。四摄默认硬件NV12保持可用，安装后的系统GStreamer／PipeWire广角取流通过。完整校准适配目标仍active。

内核只接收网格几何和增益，转换为VFE175寄存器与DMI表；调校选择、golden/unit合成和模式重采样留在用户空间。未改板级DT、传感器、V4L2核心或用户空间包，未刷写或重启。依据[317固定的原始资料](../kernel317/lsc-primary-sources.json)，未加载原厂HAL。

新增CAMSS_PARAMS_LSC=6，1792字节参数块：17×13点、R/GR/GB/B顺序、Q10增益1024～8191；间距／起点按Bayer quad表示，0～3级细分。网格必须覆盖当前Bayer sink。其它SoC保留原参数容量和路径。[UAPI](kernel/qcom-camss-config.h)、[实现](kernel/camss-vfe-175-lsc.c)、[补丁](lsc-driver.patch)。

沿用参数队列的内核快照及帧更新。在output_lock内写非活动bank的GRR/GBB表，恢复共享DMI／时钟配置后发布bank、几何和使能；启动／停止复位为关闭。旧WB/BHIST参数兼容。

S5K3M5内部灰阶彩条经过真实CSI、VFE175和NV12 DMA，不需要室内灯光。r6按参数完成序号和图像稳定条件收敛，共35帧、9阶段，不以固定帧数作为门槛。[采集](pattern-r6-capture-validation.json)、[图像模型](pattern-r6-image-validation.json)。

| 检查 | 结果 |
| --- | --- |
| 单位增益、关闭及再次启用单位增益 | 逐字恢复关闭时图像 |
| 全通道1.5倍、横向1～2倍渐变 | 幅度及方向符合模型 |
| R1.5/G1/B1.25 | 颜色通道对应正确 |
| 纵向渐变、非零x/y起点及细分 | 几何及幅度模型通过 |
| 非法标志／预留字段／增益／几何 | QBUF拒绝 |
| QBUF后破坏用户缓冲 | 不影响已复制参数 |

对39,936个平坦像素，四种非单位表的YUV模型最大误差2.403/255，99百分位不超过1.292/255。模型从关闭时NV12反推线性RGB再独立施加增益，不是独立RAW测量。灰阶重启边缘仅按基准图检测后排除，因为非线性处理在缩放前，已混合的像素不能逆推出源细节。完整图像的单位／关闭一致性仍逐字比较。

四摄分别经r25默认handler输出640×480 NV12，AE/AWB统计和参数仍工作；主摄来自r4，其余来自r5。[兼容证据](camera-compatibility-validation.json)。暗室场景仅用于取流兼容，未当作正常照明校准。安装后默认枚举及PipeWire均有四摄，系统GStreamer／PipeWire广角各12帧通过。[安装](install-r1-validation.json)。PW零拷贝未新增验证，沿用316实际MemFd结论。

首次构建缺显式UAPI include，修正后r2/r3以W=1、Werror通过。r1全亮彩条不能证明正增益，r2灰阶图确认生效；试验中的低于单位增益未衰减，最终采用原厂算法的1024～8191范围。r3的LSC通过，但消费者误写gw1未采集；r4修正s5kgw1后主摄通过，又因前摄误写imx616提前结束。实际前摄为imx471，r5剩余三摄通过。失败均恢复原模块／服务，故障增量零；未运行项未计成功。r6最终模块的完整网格检查通过。

源树`/home/cy122/x2pro-linux/camera318-lsc-kernel`，samurai-lsc318，提交`7f2de88ea5576457cd332b2383ad887e72c6698c`。[来源状态](source-state.json)、[构建](kernel-build-validation.json)。模块SHA `2f8a94f5bd34694d52a0ff262f7df668d5cbea46a2109fa5b195d510f50547fa`；加载note SHA `6ebc03a5c7a1f908252a392fdc8cf2835a78d97adf4972e575ff987ccb0a4863`。原314备份`/var/lib/samurai/k318-install-r1/qcom-camss-before.ko`。

构建／采集／安装worker均终态，PW/WP各一个进程，相机和两CCI休眠，相关故障增量0、taint0。首次安装脚本假设314前置，不在318重放。后续继续用户空间模式网格重采样、IPA合成、模组／golden绑定、个体表4个零节点与校验规则。真实个体LSC、正式光学校准、多摄几何同步、真实曝光时间及连续AF未完成。
