# 405：类型化 LTM IQ／LUT 与同请求所有权

候选内核新增`camss_a5_ipe_run_ltm_status`：复制并检查量化LTM参数，使用404几何编码，把IQ、13组LUT、CST／CC／CV和可选Gamma放入同一个保留请求。前置数组扩为最多两项，后置最多三项。**内部提交接口已实现，但未安装、未调用手机、未完成实机LTM像素验证或完整动态调校。完整目标继续，最后设备证据仍为402。**

## 接口与布局

新接口接收有名字的IQ字段、权重和量化LUT segment。普通无符号LUT为12位base／有符号12位delta，scale／LCE的base和delta均为有符号12位，逆Gamma为14位base／有符号14位delta。13组分别为weight、两组LA、curve、scale、mask、两组LCE、五组逆Gamma；各bank可独立给出。接口不接收任意硬件命令或LUT设备地址，也不把输入量化字段称为已完成原厂插值／调校数学。

类型与编码片段见[类型定义](ltm-types.h)、[编码实现](ltm-codec-tail.c)，完整[候选补丁](ltm-ownership.patch)。全部参数和地址范围在写输出前检查；逆Gamma／LA／mask／DC／IP及termination标志必须为0或1。所有LUT都校验，不能把关闭模块当作接受越界表值的理由。

新LTM路径的IQ区8944字节，按页占12288字节；旧Gamma独立路径仍6016／8192，接口和编码函数未改。

| 区域 | IQ内偏移 | 长度／容量 |
| --- | ---: | ---: |
| 通用空数组 | 2592 | 8 |
| pre数组 | 2624 | 两项，CST generic20＋LTM11 |
| post数组 | 2688 | 三项，CC／CV generic20＋Gamma12 |
| CST／CC／CV命令 | 2784／2840／2884 | 56／44／40 |
| Gamma DMI／LUT | 2928／2976 | 36／3072 |
| LTM DMI／LUT | 6048／6208 | 156／2736 |

LTM IQ仍写2096…2184的23个u32：模块enable固定为显式请求启用，其余22字段来自检查后的参数。13条DMI保持opcode1、寄存器0x5c08、selectors1…13与403核实的长度／源偏移。Gamma保持opcode1、G／B／R顺序。额外560字节原厂资源用途仍未证，没有自行扩大传输表。

## 所有权与分层

在引擎锁内先复制Gamma（如有）和2800字节LTM输入，完成检查后才分配coherent请求或进行固件MAP。条带大小及几何标志也取自LTM副本；编码后临时CPU副本在所有出口释放。DMA读取的是请求内IQ／DMI／LUT，不依赖调用方表指针；完成状态不明时沿用既有保留、quiesce及复位清理规则。

NULL LTM回到原Gamma／colour行为；旧job结构和已存在调用者保持。新API是候选SoC驱动内核接口，未接产品适配器或libcamera请求。板级、传感器及主线媒体框架没有本轮改动。

内部接口显式启用LTM，不代替原HAL的自动策略。403核实的ANR／topology enable条件、IFE／IPE输入域、CST与CCM／Gamma职责仍须由后续产品接入核对，避免重复处理；不能凭接口存在宣布当前相机已用上正确调校。

## 验证

[参数页对照](parcel-validation.json)在主机ASan／UBSan与AArch64 QEMU各运行128组、1144832字节零差，110组非法输入保持目标不变，输出尾部保持。覆盖八种colour模块组合、可选Gamma、DC／IP／mask组合、低／中／高IOVA边界及各表端值。IQ92字节与原HAL实际片段核对，DMI由原HAL完整WriteDMI／嵌套重定位生成；LUT packing参考在私有目录编译固定版本原厂函数。后者证明量化打包，不冒称运行了完整LTM数值计算。

[59个完整固件对照](firmware-parcel-validation.json)消费实际C页和404实际C几何，包含NV12／NV21、128／326／650／1920／4608／8192、单／双核、全部colour／Gamma组合，以及650宽会改变条数的DC／IP／mask组合。原HAL条带与原固件CONFIG_IO／帧准备到硬件enqueue前，整512KiB CDM和32B job全部一致；pre32、post96均只链接一次，原始IQ／LUT页保持不变。这不代替物理像素结果。

[145例请求模型](transfer-validation.json)执行当前驱动函数，含原路径、NULL LTM回退、复制后修改调用方参数、LTM／第二次分配失败、编码拒绝、MAP／帧／UNMAP状态不明及清理失败。CPU副本均释放；未知DMA保留整个请求及图像引用，未quiesce禁止释放。检查完整请求内CST／LTM／CC／CV／Gamma描述符、边界表值和复制后的几何标志。传输／分配由模型provider提供，硬件并发与故障复位仍待实机。

[源码一致性](source-model-validation.json)核对15个colour函数、6个DMA函数和15个请求／清理函数，测试body与当前源码一致；旧CC／Gamma函数体及404几何未变。候选源码见[状态](source-state.json)：`samurai-ipe-ltm-ownership405`，commit `3b65d2989ca8d71b658f8a859e8784be3e6bb965`，四文件、干净未部署。[构建](intree-build-validation.json)W=1／Werror诊断0，核心415752字节，共享配置／输出／symvers恢复。

最初将IQ与DMI片段放在同一模拟实例交替调用时，DMI夹具出现跳到地址0的模拟异常；使用独立片段实例后全部对照通过，没有修改HAL指令，也未把这当作内核或硬件故障。请求模型脚本首版沿用错的header guard名，读取即失败，按实际guard修正后运行。两者都未访问设备。

## 接续

优先以原厂资料补齐完整LTM数值／动态触发及输入域，再通过固定诊断适配器做物理LTM与CST／CC／Gamma／CV组合、像素和错误恢复验证，之后接标准media request／libcamera。工厂／个体表、HAL／固件／源码片段／命令／图像私存405及前序，不导出。

[402实机](../kernel402/README.md)的Gamma20帧及恢复正式四摄48帧继续作为最后历史证据；本轮没有采集、安装、刷写或重启。灯已打开，后续按实际光照判断。[363完整范围](../kernel363/REMAINING-CAMERA-SCOPE.md)继续：第五2MP／mux、多模式、帧长／防频闪、连续AF／光学、几何与多摄同步等未完成事项均保留。
