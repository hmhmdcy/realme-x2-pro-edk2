# 403：核实本机 LTM 契约与逆 Gamma，加入原生分区基础

恢复本机原厂LTM的初始化、13组DMI、程序类型、23个IQ字段及enable条件；直接执行原HAL逆Gamma片段，29组输入／缓存命中与保存的参考输出一致。发现启用LTM图像处理会改变分区规则和最终硬件命令，已把验证后的分区范围函数加入候选内核。**完整LTM条带、数值调校和运行时提交尚未完成；本轮未访问手机，最后设备证据仍为402。完整多摄／ISP目标继续。**

## 原厂接口与尺寸

复用本机保留HAL／固件和[固定CamxChi来源](primary-sources.json)，定点读取六文件，没有重下固件或读取NV／OTP。模型直接执行原指令；完整WriteDMI／AddNestedCmdBufferInfo沿用402经实际源缓冲类型修正的路径，只替代Begin／Commit命令存储。

[契约验证](contract-validation.json)执行原LTM Initialize的偏移与缓存初始化片段，得到13组源偏移：0、48、304、560、816、1072、1328、1392、1456、1712、1968、2224、2480。长度分别为48、五组256、两组64、五组256字节，合计2736字节。原资源初始化片段分配3296字节、sourceCmdType1＝CDMDMI；不能按资源总大小把每组表都扩大，也没有把多余560字节擅自认定为平均值表或无用空间。

原模块DMI片段与完整命令／嵌套函数生成13条、共156字节头：opcode1，寄存器0x5c08，selector1…13；三个IOVA边界条件及禁用分支通过。原提交器片段证明LTM程序位于pre-LTM数组，type11／禁用skip255，长度156。CST的普通pre程序和LTM程序需要两个描述符；当前Gamma路径pre区域仅容一项，后续组合布局必须扩展，不能直接追加造成覆盖。

原模块输出IQ2096…2184，共23个u32／92字节，覆盖enable、inverse-Gamma／LA／mask开关、bin初始化、RGB2Y、LCE／亮度比、mask系数／scale／shift、横纵终止及DC／IP开关。86组独立随机源寄存器／全位边界验证其字段宽度和相邻区域保持。`ignoreChromatixRGammaFlag`仅在值为1时清除逆Gamma字段。

另30组实际enable片段证明：模块开关成立后，还需IQ440的ANR状态等于1，或输入topology字段等于3；其它值不自动等价于TRUE。这是目标HAL的提交策略，不外推成当前Linux用户空间配置已核对。后续产品组合需明确拓扑及IFE输入域。

## 原 HAL 逆 Gamma

[29组检查](inverse-hal-29-validation.json)直接执行LTM Execute内完整逆Gamma数学与缓存片段 `0x3618a4…0x362320`。包括保存的原厂IFE green、线性、反向、全黑／全白、交替、平台、脉冲及单调／非单调随机输入；每组分别执行缓存未命中和命中。

7424字节与352保留的源参考输出零差，执行88882448条原指令；仅58次memcmp为内存比较provider，没有替换数学。352主机／AArch64可移植算法的历史对照继续复用，本轮新增实际目标HAL等价证据，没有冒称重新运行了SDK构建或整个LTM Execute。输入仍是64个IFE green基值，结果是64段14bit base／delta；不能把IPE Gamma256段曲线直接代入此接口。

首个Initialize夹具未设置已有插值缓冲指针，原函数转入尚未提供的posix_memalign路径而停止；补充已有缓冲的合法夹具状态后，初始化／命令检查通过。初版夹具私存，原HAL指令没有改动。

## 条带差异与候选底层代码

[12个常规配置](striping-probe.json)、[16个边界配置](striping-boundary-probe.json)及[两个8192宽度上界](striping-extreme-probe.json)执行完整原HAL条带及原固件CONFIG_IO／帧准备，止于硬件enqueue前。NV12、全帧1:1，覆盖128小尺寸、640／1920／4608、端口8／9、单／双核，以及324／326／328／330／648／650／656／658边界。LUT为全零的离线几何夹具，未作为物理调校提交。

启用IP后，原厂分区步长由旁路328变为324，fetch halo由4变为6，计数仍按核心数向上取整、内部边界对齐色度、从右向左排列。[30组范围核对](partitions-validation.json)无空洞／重叠。比如326宽单核：LTM两条、旁路一条；650宽双核：LTM四条、旁路两条。条数相同也会有处理裁剪、网格、径向坐标及工作量等差异。常规640×480 IP+DC配置中，旁路条带生成的最终CDM有19字节不同；边界650宽双核差1127字节且job不同。因此，命令格式正确和固件接受不足以证明旧旁路几何可用于LTM。

[内核补丁](ltm-partitions.patch)新增 `camss_a5_ipe_ltm_partitions`，与原旁路接口共用检查／范围计算，分别选择324／6和328／4。保留原旁路接口、结构和行为；非法宽度／核心数／短容量在写出前拒绝，count和尾部保持。**该函数仅产生fetch／output范围，尚未生成完整LTM blob，也未接到运行时。**

[实际候选C验证](native-partitions-validation.json)主机ASan／UBSan和AArch64 QEMU各92组、3352字节零差：26组LTM与66组旁路，后者含383保留的62组原HAL结果。内核源码 `samurai-ipe-ltm-partitions403`，commit `37040a4a11e5e3197268bdbc0c64f17e5337b592`，父402 `195f81dd30ca8865d440bafa32c7397006a436ef`，两文件，干净未部署。[源码状态](source-state.json)。

[构建](intree-build-validation.json)真实配置W=1／Werror成功，诊断0；核心390248字节，SHA `9b7488b41798872ca07d9d93bf33f8b07b38fc951228cc48d5e2b934c16d300d`。共享构建配置／输出／symvers恢复。Gamma opcode1保留，DMA／复位／请求清理、板级DT、传感器及产品用户空间未改。

## 接续

下一步以本轮原厂几何和完整CDM为oracle，把IP处理裁剪／网格／DC状态等补成原生LTM条带；同时继续原厂完整数值输入／输出复现。之后扩展类型化完整IQ／LUT布局与同请求所有权，接CST／CC／Gamma／CV组合，再做物理LTM像素和恢复验证。当前不能以新分区函数或全零离线LUT宣布LTM运行支持。

产品接入继续明确IFE CCM／Gamma与LTM inverse-Gamma的输入域，接标准media request／libcamera和原厂动态触发树。第五2MP／mux、多模式、帧长／防频闪、几何／同步、连续AF／光学等[363全部范围](../kernel363/REMAINING-CAMERA-SCOPE.md)保持。

本轮没有手机worker／帧／模块安装／重启；[最后402实机](../kernel402/current-state-validation.json)仍为正式395／393恢复、四摄48、资源释放，不能称作403新复验。原厂表、源、ASM、striping／CDM私存403及前序；source／build先storage284挂原ext4。公共镜像仅本地提交，不push／PR。
