# 426：复用四摄原厂 DS4 调校，恢复 VFE175 降采样与 PD10 寄存器编码

继续完整多摄／ISP目标。本轮从保留原厂数据中恢复四摄DS4参数，执行本机解析器、DS410及R2PD路径，并在维护内核加入对应寄存器编码器。原始指令与实际C函数768组结果一致，CAMSS和配套模块Werror构建通过。**DS4队列、DMA输出、同SOF接线及完整DC实拍仍未完成，候选未安装；没有新增现场照片。**

## 原厂数据与实际绑定

继续优先查已有固定CamxChi仓库、281保留的本机HAL及原厂GPL总线代码；没有重新下载固件、访问NV／OTP／persist。[来源与函数](primary-sources.json)、[原始函数入口](native-functions.json)。HAL内保留的压缩debug ELF已提供准确符号，因此直接定位DS410 Create／Execute／RunCalculation、PreCrop、R2PD及RoundClamp，没有按新版本布局猜旧二进制对象。

[提取器](extract-ds4.py)从保留BIN的真实目录和模式树读取四类IFE DS4／DS16模块，独立解析四份reserve数据。只在私有分析副本中关闭其它模块的解析标志，数据区和模式树保持原始字节；原厂ParameterParser导出的XML逐项相同。普通Preview／Video模式再与原模式管理器GetModule交叉核对。

| 已有物理调校来源 | DS4类根数 | 普通模式／用途上下文 | 四类模块选择查询 |
|---|---:|---:|---:|
| Sunny S5KGW1 | 4 | 4 | 16 |
| Sunny IMX471 | 4 | 2 | 8 |
| Qtech S5K3M5SX | 20 | 4 | 16 |
| Sunny IMX319 | 36 | 4 | 16 |

合计64个根、每根四份pass参数、14个已对应上下文和56次模式查询。[主摄](sunny_s5kgw1-ds4-extraction-validation.json)、[前摄](sunny_imx471-ds4-extraction-validation.json)、[长焦](qtech_s5k3m5sx-ds4-extraction-validation.json)、[广角](sunny_imx319-ds4-extraction-validation.json)。没有把Qtech GW1另算物理摄像头，没有据此认证EEPROM供应商或扩展未对应模式。

64个根包含显示及DS16模块，其系数在编码器对照中作为输入夹具。14次完整DS410 Execute只绑定实际选中的`ds4to1v10_ife_full_dc4`；没有把其它标签送入这条生产绑定，也没有实现或验收DS16硬件。

完整执行本机`chromatix_ds4to1v10TypeClass::Parse`得到200字节运行时对象，64个对象的四份pass数据均与独立BIN读取一致。[指令模型](ds4-model.py)随后执行完整DS410寄存器计算和R2PD Execute。内存读取跟踪确认DS410读取对象+140／144／148，即PASS_FULL的三项系数；不是从四份数据中任选一组。14次完整Create／Execute还核对实际模块名、reserve绑定与使能掩码。该Unicorn路径的GetModule由框架provider返回外部原管理器已经选定、且经本机Parse生成的对象；寄存器传输也由provider记录，数学和依赖更新仍执行原始指令，未声称Unicorn内部又运行了全部模式管理器。

## 底层代码与验证

新增[DS4编码器](camss-vfe-175-ds4.c)及类型头，加入正常CAMSS的Kbuild。输入为明确高度、三项已选调校系数和原寄存器值，输出依次为Y配置、滤波、C配置和R2PD配置。系数按schema检查单项及总和范围，没有固化任何模组系数。保留无关位，PD10切换会清除旧PD8模式位；校验失败不写输出，允许原地更新。

这个函数**只构造寄存器值**，没有MMIO、打开模块、注册DS4输出、启动DMA或生成像素。上层仍须先保证裁剪、缓冲和所有权完整，再调用并实际应用。内核UAPI、板级DT、传感器和用户空间未改。[完整补丁](ds4-register-codec.patch)。

[实际函数对照](codec-validation.json)覆盖64份原厂根、四个高度边界和三组寄存器原值，共768组／12288字节。宿主ASAN／UBSAN和ARM64静态qemu均与本机完整DS410／R2PD原始指令逐字节一致；每架构10项非法参数保持输出，原地输出与独立输出相同。包含非零旧寄存器，验证字段保留和PD8→PD10模式清除，不只是零初始化例子。

维护分支`samurai-vfe175-ds4-codec426`，最终提交`dbefc5bdd8de8da07128171423f098a38d6e45b0`。[源码与补丁](source-validation.json)零fuzz／零offset复现，维护树干净；实际CAMSS模块存在`vfe_175_ds4_encode`，不是仅构建宿主测试副本。[构建r3](intree-build-validation.json)48.30s、W=1／Werror、零诊断，CAMSS、core、adapter及7个匹配媒体helper共10模块成功。CAMSS候选SHA256 `101cc9b977d5c7582215391772130c19393b38150708b8fe888d0bdda9081d44`，core与425逐字节相同。共享构建目录及原来不存在的产物均已恢复。

首次构建发现缺少显式`linux/bits.h`，已单独提交修正；第二次因只请求CAMSS／core，modpost缺少匹配的VB2／ISP／m2m符号。确认两次均终态并恢复输出后，补齐已有模块目标，第三次通过；没有忽略符号错误或降低Werror。[r1](intree-build-r1-validation.json)、[r2](intree-build-r2-validation.json)。

## 已确认的生产配置与尚缺的接线

[完整原厂裁剪／深度／打包执行](producer-geometry-validation.json)覆盖128、640、650、1920及4096宽五组几何：DS4 Y／C滤波配置在0xd60起；前裁剪0xd84／0xda4；DS4独立round/clamp在0xd98／0xdb8，保留10位且不右移；PD10 pack mode为0，R2PD在0xd6c。原始指令按相同calculated frame串联DS410→PreCrop→RoundClamp→R2PD后，模块使能在0x4c对应掩码0x5500。这些是寄存器配置和因果路径证据，不是像素产出证据。

保留的本机GPL总线代码确认DS4使用WM5、单平面、packer0，活动宽度按`align(pd10_width * 4, 16)`字节，高度为`pd10_height / 2`；backing步长／slice仍按425本机HAL规则192字节／4打包行。不能把WM活动宽度等同于buffer stride。

下一步直接补VFE175 DS4格式／输出注册、WM5传输、队列及停止回收，使用本轮原厂系数和已恢复控制配置；绑定FULL的MNDS／裁剪与共同SOF。当前通用额外节点注册只处理stats／params，VFE175注册FULL／params／stats三个输出；需要真正增加图像输出节点及准确的PD10格式描述，不能借用NV12或伪造元数据格式。现有SOF标签遍历全部活动输出、组合完成处理和SG范围检查可以复用，仍需验证新增路径的断粮／重开／回收。

再把真实PD10缓冲接入425已确认的IPE粗级端口、完整C multipass striping、scratch容量及session／frame所有权，验证DC统计产出和全尺寸IP消费，最后合入IPA触发／最终成功历史并实拍。上游GTM的原厂非零份额、IFE生效版本与对应图像IPE的因果绑定仍缺；完整范围见[剩余项](../kernel363/REMAINING-CAMERA-SCOPE.md)。

本轮没有访问设备；最近实拍仍为424的410帧／402数值提交、两次AF Focused，雾感和偏色未解决。正式420 r31／r26、419驱动和Image363／DT389／CAMSS389未被本轮修改。所有原厂系数、完整运行时对象、XML、寄存器流和照片仍仅存私有目录。
