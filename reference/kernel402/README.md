# 402：修正原厂 Gamma DMI 格式，实像素验证通过

原厂 Gamma 类型化接口完成首次物理验证，并通过对照实验修正401的命令格式错误。第二次事务20帧中，线性、零值、半幅、分通道、常量及一条原厂曲线符合预期；NV12／NV21归一化全部一致。随后恢复正式395／393，四摄48帧与资源释放通过。**这是固定诊断组合的Gamma验证，完整自动调校／LTM／光学和多摄目标继续。**

## 首次失败与实际原因

首次 `/var/lib/samurai/k402-gamma-r1` 临时使用401核心和固定Gamma测试适配器。20帧均正常完成，协议／看门狗错误为0，随后正式四摄48帧通过；但Gamma像素失败：线性与旁路最大字节差194，零LUT不是黑场，常量LUT不是常量，格式归一化也不一致。[失败像素记录](pixels-validation-r1.json)、[首次传输与恢复](runtime-validation-r1.json)。传输记录的passed只表示提交／回收／恢复，不覆盖像素正确性。

原厂 Gamma `FillCmdBufferManagerParams` 初始化片段直接写入源缓冲类型 **1＝CDMDMI**，大小3072字节。401夹具先假设类型3＝CDMDMI32，再执行完整WriteDMI，因此错误选中旧式opcode10。401所谓“原厂实际opcode10”的结论撤回；原模块三通道、数值曲线、寄存器和地址重定位记录仍成立。使用真实类型1，原模块片段、完整WriteDMI及AddNestedCmdBufferInfo生成 **opcode1**，三条12字节头、每通道1024字节，寄存器0x6008，selector1／2／3及源偏移0／1024／2048保持。[原初始化与完整命令验证](dmi-correction-validation.json)。没有修改原HAL指令。

另直接执行原固件完整AddBLs及其真实累加器函数，UID0与1均生成相同Gamma DMI和0x6058／0x605c bank选择；UID0走强制编程，不支持“UID0跳过首次LUT”猜测。该离线检查无替代provider，摘要见[下游检查](downstream-validation.json)，完整指令／包私存。

[唯一核心修正](gamma-dmi-correction.patch)将固定DMI头从0x0a0003ff改为0x010003ff。源码 `samurai-ipe-gamma-dmi402`，commit `195f81dd30ca8865d440bafa32c7397006a436ef`，父401 `b8ce3ce92745a11b039e1335e87bbb2dd783c2c7`，仅一个文件，干净未永久部署。[源码状态](source-state.json)。所有权、8192字节IQ分配、typed LUT校验、free／unknown-DMA／复位、板级DT、传感器和用户空间均未更改。

## 第二次实像素

首次事务已确认终态并恢复正式驱动，之后才新建独立 `/var/lib/samurai/k402-gamma-r2`，没有重启旧worker。两次使用完全相同的测试adapter和client，只替换修正后的核心。私有固定CST／CV对复用400，CC为单位；原厂Gamma采用保留曲线中的第一条作诊断，不冒称当前场景触发树选出的曲线。

640×480，NV12／NV21各十种模式，共20direct／starts-stops20，错误0。[像素检查](pixels-validation.json)：

- 普通程序类型20的转换对输出，与400单位CC对照全460800字节一致。
- 线性Gamma与不启用Gamma仅100字节不同，最大差1；八个灰阶块一致。
- 零LUT全图Y=0／UV=128；常量512 LUT全图Y=128／UV=128。
- 半幅相对线性和编码黑色，全Y／UV的 `2*half-linear-zero` 仅−1／0／1，即输出误差至多半个量化级。
- 单独保留G／B／R通道的24个灰阶检查，与已验证CV系数的预测最大Y误差1，支持selector1／2／3对应G／B／R。
- 原厂曲线八个灰阶点与原HAL量化LUT预测误差0，且确实改变像素；未发布原厂表值。
- 十种模式NV12／NV21归一化所有字节相同。主机重算CRC、输入生成器、输入未改、输出尾canary、sequence和timestamp检查通过。

每帧独立stream start／stop，包含16次Gamma启用请求，LUT随请求重新装载；这不替代带Gamma的强制故障复位／丢ACK验证，也不支持所有尺寸、矩阵、饱和与舍入的普遍结论。驱动没有CPU图像处理。

## 构建、恢复及边界

修正后[参数页](parcel-validation.json)主机ASan／UBSan和AArch64 QEMU各3450组／9993772字节零差，6040个非法Gamma输入不写输出；[生命周期](transfer-validation.json)85例通过；[完整原固件准备](firmware-parcel-validation.json)19例与当前C条带的整512KiB CDM／32B job一致，止于硬件enqueue前。离线通过与实像素证据分别记录。

[正常核心构建](intree-build-validation.json)W=1／Werror诊断0，388520字节，SHA `31d203159178b413fd247aa240910558c566417ad424f5e4ab4f274cc069c5d2`。测试适配器114384字节，SHA `4bfbb80fcfefc50aa770b0c39c49f4c016093dda95da82c11e43144030fefe5a`，只暴露十个固定选择，原厂数值头私有；无任意寄存器／CDM接口。共享构建配置／输出／symvers和正常源码恢复，辅助模块仅构建未安装。

第二次[runtime](runtime-validation.json)和[恢复核对](current-state-validation.json)证明：正式核心395／适配器393恢复；r30四摄各12，共48direct／starts-stops4／error0／extra0；CPU／IRQ／PM／backing／maps／import释放，ICP／CAMSS／双CCI suspended，17clks0、9rails disabled／users0，taint0。PW16240／WP16247各一uid10000；owner_refs53来自桌面CAMSS句柄。两次collector均终态、无dump／timeout，无新增相关fault、重启、刷写或永久安装。最终worker15997／collector16092及client全部终态，勿重启旧事务。

两次各native20＋恢复48，合计136direct分属不同模块epoch；最后正常epoch只计48。首轮16个Gamma请求的像素失败保留，不能把136写成全像素通过。首次主机r2分析脚本误把历史400样本路径也替成r2，出现FileNotFoundError；修正分析路径后复用已保存样本，不重复手机实验。

分层仍明确：本轮修正在SoC IPE命令编码层；板级、传感器和主线框架未变，产品libcamera未接新Gamma参数。正式默认仍旁路高级IQ。下一步补原厂LTM完整enable／DMI／inverse-Gamma／参数所有权，再组合完整调校；接产品前依据[401 IFE／IPE职责审查](../kernel401/ife-role-audit.json)定义CCM／Gamma处理位置，避免重复应用。接标准media request／libcamera及动态触发树，继续[363所有剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)：第五2MP／mux、多模式、帧长／防频闪、连续AF／光学、几何／同步等。

原FW／HAL／OEM／ASM／命令／图像／个体校准私存402及前序；原厂固件、NV／OTP和备份保持。用户已开灯，现场样本按实际光照评估。公共镜像只本地提交，不push／PR；source／build继续先storage284挂原ext4。
