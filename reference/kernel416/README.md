# 416：真实 IPE 版本绑定、HDR 输入域及完整 SWTMC11 执行

纠正415的一处基址误判，验证实际请求版本绑定和HDR输入域，并把已复现算法组合成单进程数值步骤，与原厂完整SWTMC11 Execute的连续状态逐字节对照。用户空间适配继续；内核／板级／SoC／传感器／DMA／产品默认均未改变。手机访问、新硬件帧均为0，最后实机仍[406](../kernel406/README.md)。完整目标未完成。

## 纠正请求版本来源

415把`0x2cfa9c`当作请求版本写入，错误在于直接使用`SP+0x240`作为ISPInput基址。实际原厂`0x2d7a64..0x2d7a70`以`SP+0x340`传入模块Execute；`0x2cf504..0x2cf514`也对该起点清零19928B。因此前一基址早256B，该64位字段是实际ISPInput+2760的调校管理器指针，**不是版本表**。415公共说明已加更正，不再追逐该错误来源。

真正绑定为`0x2d6564..0x2d6590`：从node+0x14938辅助基址的+116读取ADRC缓存版本（即node+0x149a8+4）；仅当version==1时，把请求版本设为1，否则保留初值；正常清零请求初值为0。始终把node+0x149a8缓存指针绑定到请求+3024。未知元数据版本不能照新版代码直接cast为请求版本。

[binding-model.py](binding-model.py)执行真实初始化、绑定及HDR转换指令，保留前后guard。16种版本／初值组合确认：缓存版本1覆盖为1，0/2/UINT_MAX均保留初值。这是二进制逻辑验证，没有观察Android当前metadata或运行相机。

## HDR 的实际输入域

`0x377120..0x3771b8`从AEC两个曝光槽读取：槽0的time/gain/sensitivity偏移0/8/12，槽1为24/32/36。输出请求2872为float(time1)/float(time0)，2876为gain1/gain0，2880为sensitivity1/sensitivity0。time0为0或浮点分母abs小于1e-9时相应比值保持1。槽的Long/Short语义名称没有凭新版枚举假定。

结合415已执行的模块触发更新，确认TMC11 module88接曝光时间比、module92接灵敏度比。HDR control0/1分别选这两个比值；control2在本机模块仍使用零，不能把已存在的2876曝光增益比直接塞进去。

[input-validation.json](input-validation.json)：1,002个目标数值用例、4个非法输入；两项有限输入产生非有限比值，公共实现原子拒绝。包括uint64→float舍入边界、零／负零、1e-9相邻float、宽幅数值和随机曝光对。主机ASan／UBSan、ARM64 SDK／QEMU各20,120B零差，目标35,588指令，仅16次memset provider。

## 完整函数与连续状态

[execute-model.py](execute-model.py)调用原厂入口`0x383728`，从函数序言执行到实际RET；包括根依赖更新、编译Gamma初始化、触发／锁策略、三层插值、直方图与膝点生成、版本及ADRC输出。提供已分配并清零的4236B ADRC存储，未替换分配器、根选择器或数学控制流；数学函数logf/expf/powf仍用host libm，非Bionic。

[execute-runner.cpp](execute-runner.cpp)在同一进程组合415状态策略、414树、413生成、415元数据缓存及416版本绑定／LTM选择门槛。输入输出显式，保留旧ADRC中未写入字节，输入不变；结果为候选状态，没有提交到实际产品请求。树、Gamma、权重和两份统计缓冲均由私有调用方传入，公共库没有原厂数组。

[execute-validation.json](execute-validation.json)覆盖四个物理变体、14个已知普通Preview/Video上下文，各11步共154次完整原厂调用，全部返回成功；其中72步重新计算。每架构比较1,316,392B，主机ASan／UBSan和ARM64 SDK／QEMU均零差；原厂Execute执行17,899,720指令，传输／绑定／consumer另14,384指令。

序列包括只换hist、相等触发force、锁定时更新缓存、解锁后保持、force使用已缓存hist、缺失属性、变UID关闭／恢复、同UID反转enable不刷新以及灵敏度比变化。14次属性缺失、UID／enable切换均为明确合成条件，不是现场故障。原厂根和全部原厂数组保持，UID／enable仅在私有测试副本修改。416没有重跑412根选择器，复用其14上下文选择证据。

12步出现模块版本0但ADRC对象仍保留版本1，IPE随后仍按缓存头绑定版本1。这证明模块状态、生成对象、元数据缓存与请求绑定需要独立管理；不能把“模块已关闭”当作旧ADRC已失效。缺失属性也只清缓存enable；本轮组合保持原厂字节语义，产品接入必须另外验证来源、新鲜度及请求归属。

## 当前边界与推进顺序

这是完整SWTMC11函数及已知输入／缓存链的离线对照，没有运行整个IFE发布器／整个IPE Execute，没有验证分配失败或实际硬件调校。统计来自两份合成、不可变缓冲；现场统计域和缓冲生命周期仍须核对。完整TMC／ISP产品、默认开启与原始完整目标继续保持未完成。

接下来优先把已核对数值接入可运行的候选请求路径，并以实机非零调校、连续参数和资源恢复作为验收；先定位该路径实际需要的LA/mask/weights/scalars、inverseGamma、IFE/IPE输入域／统计缺口，再针对缺口补齐，避免重复展开已通过的TMC离线用例。408 raw124/140身份与候选state提交仍需解决。

[363完整范围](../kernel363/REMAINING-CAMERA-SCOPE.md)不变：第五2MP身份mux、多模式／帧长／防频闪、自动／连续AF和光学、几何／多摄同步、标准media request/libcamera与稳定性。用户已开灯；后续现场样本按实际曝光和照明解释。全部原厂数据、汇编、原始输入输出在`/mnt/e/edk2-samurai-out/kernel416`及前序私有目录。公共检查点仅本地提交，不push／PR。
