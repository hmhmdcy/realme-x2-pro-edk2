# 351：恢复原厂 LTM、后级矩阵及逆 Gamma 默认开关

2026-10-20。继续从保留原厂调校BIN/HAL恢复数据，未要求色卡。本轮新增完整LTM和IPE CCM提取，以及实际HAL静态开关复现；没有安装相机软件或改动默认调校。完整多摄/ISP目标仍在推进。

五份BIN共提取149个 `ltm13_ipe` 根/2135个调校区域、43个 `cc13_ipe` 根/737个矩阵区域，与原厂ParameterParser的全部触发树、控制轴、开关、reserve和数值一致。完整表和XML只私存kernel351及E盘ext4的parser351工作目录。[完整提取](factory-colour-chain-validation.json)、[固定来源](primary-sources.json)。

LTM序列化root为872字节，reserve起点88、大小768；动态核心是DRC/HDR/AEC三层，不套用Gamma/CCM的LED/CCT层。按固定schema的实际存储类型解析并核对XML：部分核心数组虽标为int，`tool_hint=float`对应float字节。初版按int解读时XML核对失败，已改正，首份不匹配结果私存。IPE CCM根144字节、CCT叶72字节，与既有IFE CCM12形状相近，但保留独立模块及所处处理级，不直接替换。

复用已对应的7个物理模式、Preview/Video共14个上下文；28次LTM/CCM选择与原厂管理器完全一致。全部选择LTM根42，调校中module/LTM/inverse-Gamma/数据收集/图像处理均开启；CCM启用、qfactor0。主摄mode2选CCM47、mode4选176，其余普通模式选47。各模式Preview与Video完整数据相同。[模式对应](mode-colour-chain-validation.json)。这些是调校选择，仍区分Android运行时覆盖。

所选主摄、广角、长焦的后级CCM均为单位矩阵；前摄28个区域有25组不同的非单位矩阵，offset均0。前摄IFE矩阵关闭，与其在后级执行颜色校正的调校安排相吻合。不能通过打开原先禁用的IFE矩阵来代替这组后级矩阵。LTM各所选模式存在非零局部色调强度/scale区域，也不能无依据当成直通。[所选配置分析](selected-profile-analysis.json)。

从原HAL恢复两项静态标志，不再只依赖较新参考源码默认值。执行原 `HwInitializeDefaultSettings`，从零与全1对象输入都得到其实际低22bit默认值；LTM构造片段读取15632偏移的bit18/19并写入自身620/624槽位，原构造日志的W6/W7参数确定它们分别是`ignoreChromatixRGammaFlag`和`useHardcodedGamma`。两个编译默认均FALSE。[实际HAL开关](static-flags-validation.json)。

还执行完整 `HwLoadOverrideSettings`，只替代虚拟设置存储读取，44次读取/函数；恢复两项hash key，并核对开关四种组合到构造对象的结果。累计31601条原始指令。没有运行Android服务或原厂二进制本机代码。此项证明编译默认和该覆盖路径，不宣称已经观察Android属性覆盖后的实际状态。

为找原厂文件覆盖，只读ro/noload/noexec挂载手机vendor，检查`etc/camera`和`etc`中的camx配置名及两个明确候选路径；没有找到camx设置文件，已卸载并移除临时挂载点。没有把“文件未找到”推断为所有运行时覆盖都不存在，也没有读取NV/OTP/EEPROM/persist。[本次读取结果](vendor-settings-validation.json)。没有重读HAL或大调校BIN。

因此，目前可依据原厂调校和实际HAL编译默认建立：IFE Gamma信息供LTM逆变换，LTM处理后再经IPE矩阵及Gamma。完整物理执行/锁存和Android最终覆盖仍要分别验证；较新源码列表不替代目标运行观察。现有VFE后端没有完整IPE LTM实现，不能简单合成两条Gamma后宣称复现原厂最终画质。

本轮没有修改板级DT、传感器、主线框架或SoC驱动；350数值工具、348内核和349 IPA候选仍分别保存。已部署基线仍沿用349最后观察的CAMSS338、r27/r22与344私有默认；本轮手机操作仅为上述只读vendor挂载，未改安装文件/模块、未重启或刷写。下一步优先复现LTM逆Gamma/核心数学与前摄CCM13输出域，并据此选择硬件支持或明确近似的后级方案；Gamma尚未启用为新默认。曝光表、防频闪、实际传感器限幅、更多模式、光学/几何同步、连续AF仍未完成。
