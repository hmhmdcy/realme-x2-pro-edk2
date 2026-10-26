# 286：VFE175 FULL位深转换与Gamma16后端

后续[287](../kernel287/README.md)已增加Demux/MNDS16，候选6ddf1ba4c完整构建通过；未部署仍3RDI，输入域和硬件图像待验。本文最新源码/输出按286时点阅读。

2026-10-19。完整多摄及骁龙ISP目标继续。本轮从干净d1a5f8440候选继续，实现FULL RoundClamp及Gamma16，完整构建通过。**未部署或开放PIX，尚无Spectra硬件成像。**

## 依据及边界

先检查285当前Git HEAD/工作区、构建终态和来源收据，再查已有方案。较新IFE的DMI地址和OPE256×u8曲线与本机不同，继续使用公共CAMSS框架并补175后端，没有把其它硬件布局直接套入。

[寄存器静态核对](register-contract-validation.json)重新断言本机原厂HAL SHA e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde的35处实际指令及跳转表。原厂GPL内核固定9668fcdc6ec15be7a10d66f7b93c347829e0fdb6的CDM util提供直接32位DMI低端口为CFG+12的依据。网络初次两个文件路径404、四个参考SSL EOF均保留；随后用已有官方bare Git取得正确CDM文件，并成功重试三个固定版本参考，不构成阻塞。

- FULL Y/C使能分别为 **0xe0c/0xe2c bits10/11**，来自calc+980/+984的实际指针链；不是0x44，也不是猜测相邻全局寄存器。
- Y配置对0xe18/0xe1c、C对0xe38/0xe3c；clamp min9:0/max29:20，round bits5:3、pattern2:1、interleaved0。**最大值位域与CST不同**；输出8位时clamp最大255。
- Gamma64个原生32位字/65节点，低10位base、上10位有符号delta[-512,511]，只有终节点可达1024。LUT cfg0x798 bits0…2，使能0x48 bit3；DMI cfg0xc24、addr0xc28、低端口0xc30，G/B/R bank0选择26/28/30。
- 每项显式写DMI地址，不假定自动递增位；选择宽度按CDM u8协议处理。**DMI实际端口行为、物理颜色及各通道bank对应关系仍需硬件验证**，主机模型不替代它们。

原HAL、反汇编和带专有声明的CamxChi参考私存，只用于布局交叉核对；无OEM运行库执行、无复制原实现、无OTP/校准写回。[可重核脚本](verify-register-contract.py)、[原厂GPL仓库](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source)、[传递函数标准公式](https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/colorspaces-details.html)

## 源码及分层

树 `/home/cy122/x2pro-linux/camera279-isp-kernel`，分支 **samurai-vfe175-depth-gamma286**，HEAD **209d1ea0f0a53e9a725ad288c159baddbc83aef7**。实现提交f2626cc3c，随后209d1ea0f仅补屏障说明；不重写已保存提交。组合补丁基于285/d1a5f8440。[补丁](vfe175-depth-gamma-candidate.patch)、[来源/独立index重现](depth-gamma-commit-validation.json)

| 层 | 变化 |
| --- | --- |
| SoC输出后端 | RoundClamp仅SM8150 full VFE175，8/10位内部配置先验端点、后MMIO；NV12 prepare使用8位，Y/C共享pattern3、C交错；两组使能读改写保留crop/scaler位 |
| SoC Gamma后端 | RGB顺序的65节点内部配置→64字打包；所有节点及斜率在任何MMIO前检查，不静默饱和错误曲线；从标准xfer_func选择sRGB/709/线性初始曲线 |
| DMI/使能 | 填各通道未使用bank，逐项写地址/低端口，恢复原DMI cfg和addr，屏障后切LUT bank，再启Gamma；不提前PIX RUP，不使用64位高低字交换 |
| 生命周期 | pixel prepare先验CST/Gamma格式，再Demosaic→Gamma→CST→RoundClamp→中性WB；失败统一清处理使能，主FULL停止同样回收；metadata stop不关闭主处理，RDI零处理MMIO |
| 保持项 | 五个WB函数、CST和Demosaic文件与285父版本逐字一致；公共参数仍仅已实现WB，不宣称Gamma per-frame接口已经接通 |
| 板级/固件/用户空间 | 无DT、固件或应用补丁，无新UAPI/私有节点。仍三个RDI资源，尚未接libcamera硬件ISP pipeline/IPA |

Gamma上传是**输出启动前的初始化接口**。当前没有并发DMI消费者；后续加入每帧Gamma、LSC、统计等时，必须落实共享端口串行化及帧级bank生命周期，不能直接把当前prepare函数放进IRQ参数回调。标准传递函数不包含传感器CCM、模组黑电平/阴影/噪声或场景色调调校。

## 主机验证及实际限制

[实际函数ASan/UBSan](depth-gamma-host-tests-validation.json)：

- RoundClamp四字段在8/10位分别遍历所有65536输入，共524288项；无效位深、反向端点、保留位、配置→屏障→Y/C使能及停流清理。
- Gamma全部1024²相邻10位节点对、全部195节点的边界探针、首节点全部65536输入、终节点1024/1025及不对称signed10边界；配置错误零MMIO。
- 三色不同曲线、八种原bank组合、自动递增开/关模型；每个非活动bank的64字精确匹配，原活动bank不变，DMI状态恢复，LUT先完成再发布，disable不上传。
- 三种传递函数全部65节点与独立浮点方程比较、16385点插值模型；当前导出V4L2 UAPI、CST四矩阵143748点、Dem/WB及实际17x enable/stop/失败回滚继续通过。

**64段均匀插值的模型误差**：sRGB最大20.048757、709为2.986662、线性0个10位码值，不含硬件舍入。节点量化误差≤0.5不等于整段误差≤0.5，不能据节点测试宣称画质达标；仍需GTM/输入归一化及IPA调校联合处理，硬件采集确认实际输入域和插值行为。本轮未取得新样片。

测试生成脚本初次三引号语法错误，在执行测试前终止；修正后通过。首轮checkpatch还提示三处屏障缺注释，补说明并以新提交重跑主机测试后仅剩通用MAINTAINERS提示。原首次报告和checkpatch私存；没有以禁用内核告警绕过产品问题。

## 正式完整构建

[Kbuild收据](depth-gamma-full-build-validation.json)：93.09秒、两阶段终态exit0。**37组件W=1/-Werror及完整Image/778实际ko/DTB均成功，本次增量诊断0。** 不以此覆盖282从头构建的1140条历史warning。

- Image44235264字节，SHA **33e51409d2074b0ba75b7bc7a6003ea91bb1c32e02d21b98ecae7dda785355e0**。
- DTB114556字节，SHA仍 **dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d**；config0c26bd91…保持。
- modules.order所列`.o`逐一映射实际778个`.ko`并哈希；qcom-camss.mod实际包含新增round/gamma两个组件。模块哈希私存。
- 合成补丁从d1a5f8440在独立index重建HEAD完整tree；checkout/index干净，checkpatch0 errors/1新增文件提示，CAMSS目录条目覆盖；未推送。

只重挂已核backing的既有E盘ext4构建卷，未格式化。编译前按285收据核验并另存六项产物到私人`kernel286/completed-cst285`；282完整778ko归档、284/285备份保持。最新输出 **/mnt/samurai-full282/build**，release仍 **7.3.0-rc6-rmx1931-samurai-k279candidate+**，不能混入现机k132+模块。构建会话73742已终态，旧PID不作为续作活任务依据。

## 现机及下一步

[只读健康](final-health-validation.json)：仍boot276/Image183、776模块/961包、libcamera r24/config-r19。50载荷/全部模块保持、十个加载note匹配，原桌面/PW/WP进程保持；四sensor/lens/双CCI/CAMSS suspended、九rails及共享I/O/clocks回收，fault0/taint0/pstore空、无CCI错误，SSC/SensorProxy正常。本轮无手机安装、刷写、重启、取流或调焦；运输用[host.py](host.py)，保持276 guard。

已取得固定CamxChi版本的Demux13/MNDS16六个布局参考及本机MNDS16两段有符号静态反汇编，私存`kernel286/next-normalization-sources-private.json`等。Demux13配置有四种CFA周期/模式、左右增益与输入/输出黑电平；不能只凭RAW10名称就盲目设16倍增益，应先核CSID/CAMIF对齐与14位内部域。MNDS需核尺寸-1、插值分辨率、相位及NV12色度二分采样，不能只启动Y/C writer。

续作从209d1ea0f继续Demux/输入位深、MNDS缩放与色度抽样、GTM/CC、真实统计/参数及libcamera pipeline/IPA，然后TPG/RAW硬件验证DMI、通道/范围、曝光/画质和功耗。继续四摄GUI/录像、AF加速/Continuous/距离标定、Shine OV02A1B确认和统一Image/rootfs；GPU/modem watchdog开放项保持。当前仍RAW→CPU ISP，完整目标active，尚不能承诺无补丁升级。

implement/save/polish/build脚本均已执行，不直接重放；build/backup有存在性保护。下一轮先用284/storage.py核挂载，再访问输出，不能写入空挂载点。source/为独立实现模板，Gamma标准表由implement脚本数学生成；最终真实源码以组合补丁/提交为准。
