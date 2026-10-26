# 415：TMC11 状态／版本策略、IPE 元数据缓存及 LTM 选择分支

按本机原HAL恢复三部分逻辑，并在主机与ARM64逐字节核对：TMC11依赖更新、4236B ADRC元数据拷贝、LTM选择自身TMC10或上游数据。新增代码属于用户空间适配；SoC、板级DT、主线、传感器、DMA、内核及产品默认均未改动。手机访问／新硬件帧为0；最后实机仍[406](../kernel406/README.md)，完整多摄／ISP目标继续。

## 本机状态策略

[policy-model.py](policy-model.py)执行`0x383728`完整入口到开始插值`0x383cdc`或无计算出口`0x38565c`，使用已有ADRC存储，不替换任何函数，不执行原厂分配器。候选调校根由调用方提供，本轮没有调用根选择器。数值插值／生成沿用[414](../kernel414/README.md)及[413](../kernel413/README.md)，本轮没有重复其全量测试。

本机只在缓存为空或SymbolTableID改变时更新根及moduleEnable，不含公开新版源码新增的enable变化比较／动态使能策略。moduleEnable原始值直接写入请求`+3016`版本字段，只有恰为1才计算。六个触发缓存按float绝对差、转double与`1e-9`比较；任一变化更新全部六值，有新直方图指针才替换旧指针。仅forceUpdate且触发相等时会重算，但不刷新直方图指针。

即使关闭，已有ADRC指针仍发布到请求`+3024`，而模块计算指针清零；不会清空旧ADRC对象。AE／AWB锁字节同时恰为1时，禁止计算发生在缓存／版本更新之后。因此“关闭／锁定／未计算”和“上游ADRC对象内容已清零”不是同一状态。便携接口输出候选状态，不直接发布到产品请求。

## 原厂元数据与 ABI 纠正

此前“ISPInput+112为ADRC头”标签不准确。`0x2d0050/54`构造`0x14938`，`0x2d0150/58`把`IPE node+0x14938`保存于SP+408；`0x2dffe4..0x2e01f8`写其+112。因此真正ADRC缓存首地址是**node+0x149a8**，版本在其+4。后续膝点、系数、对比度曲线等也落在该连续4236B对象内。[metadata-model.py](metadata-model.py)以此地址执行原厂传输并检查前后边界。

版本0拷32B膝点，保留联合体尾部8B；版本1拷40B；未知版本保留旧膝点，但仍拷头及其余公共区域。属性缺失只清enable，不清版本、ltmEnable或旧数组。[缓存适配器](libipa/tmc_runtime.cpp)明确保留这些字节语义，包括未知版本／旧字节；这只是wire兼容层，不是数据验证器，也不授权向硬件提交。产品接入仍须核对版本、来源、新鲜度和请求归属。

415曾把`0x2cfa70..0x2cfaa0`解释为请求版本全局表来源；**416已证实并纠正这一误判**：此处基址比真正ISPInput早256B，写入的是实际+2760调校管理器指针。真正版本绑定在`0x2d6564..0x2d6590`，缓存version==1才写请求version1，详见[416](../kernel416/README.md)。元数据头、模块版本与IPE请求版本仍须分别解释；本轮没有观察Android实际运行版本。

## LTM 选择与验证

执行实际`0x360088..0x35e9dc`分支；当TMC10根存在、enable恰1、use_ltm恰1且请求version为0时，进入`0x363988`自身TMC10路径。否则读取上游ADRC指针，复制其ltmEnable并保持原changed状态；此片段没有再检查上游global enable或version。自身TMC10路径只验证选择门槛及进入后的flag写入，尚未执行该路径的分配及完整计算；TMC10数值证据仍是411。

[runtime-validation.json](runtime-validation.json)全部通过：

- 状态策略733有效／7非法，含68根的136次enable／锁定用例、405缓存／force／锁矩阵及192阈值／直方图保留用例。原厂169,658指令、无provider；各架构44,400B零差。
- LTM门槛1,152有效／3非法，16次自身TMC10分支；各架构18,480B零差，含raw enable／version非0/1及上游global enable为0的输入。
- 元数据63有效／1非法，含413已保存的三份实际生成输出，其余为合成字节及旧缓存。各架构271,360B零差。原厂元数据＋选择门槛18,117指令，仅51次memcpy provider。

主机ASan／UBSan、ARM64 SDK／QEMU均使用`-ffp-contract=fast`；输入保持、失败输出保持、元数据前后边界／别名拒绝核对。原厂源代码、缓存和参数原件、汇编及测试字节仅私存`/mnt/e/edk2-samurai-out/kernel415`及前序目录。公共库不包含原厂数组。

[固定源码来源](primary-sources.json)补看IFE发布、IPE读取与请求填充、Titan170创建表。该公开版本已使用SWTMC12，作为结构参照而非本机功能证明。

## 继续

416已纠正`0x2cfa9c`基址误判，并补齐真实版本绑定、HDR88/92域及完整SWTMC11 Execute连续状态对照，见[后续证据](../kernel416/README.md)。真实producer发布、现场元数据／请求归属、408 raw124/140和请求state提交仍待完成。

LA/mask/weights/scalars、逆Gamma、IFE/IPE输入域／统计粗级、非零完整调校实像素、连续参数／故障恢复和标准media request/libcamera继续。[363完整范围](../kernel363/REMAINING-CAMERA-SCOPE.md)保持，含第五2MP身份mux、多模式／帧长／防频闪、连续AF／光学、几何多摄同步。完整运行版、完整LTM、产品与默认提交仍未完成。
