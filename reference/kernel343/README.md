# 343：原厂模式树与普通取流曝光表选择

2026-10-20。已恢复原厂模式表的结构和选择行为，并把七个已有物理几何依据的传感器模式对应到明确的 Preview/Video、无附加 Feature/Scene/Effect 上下文。普通持续取流选择曝光表 0 已由保留原厂 AEC 指令确认。生成八份私有配置，覆盖现有调校中的五个已对应模式；本轮没有改手机文件、内核、软件包或默认配置。部署继续为 342 的 r27/r22，完整适配目标 active。

首先沿用固定版本的 [CHI 模式定义](https://github.com/bjzhou/CamxChi/blob/9f17f1b568626b393e785b369c5dc94543774d7a/chi-cdk/api/common/chituningmodeparam.h) 与 [FillTuningModeData](https://github.com/bjzhou/CamxChi/blob/9f17f1b568626b393e785b369c5dc94543774d7a/chi-cdk/core/chiutils/chxutils.cpp)。它们把传感器索引和 Usecase、Feature、Scene、Effect 分层传入选择器；不是把输出尺寸直接当调校编号。[精确来源](primary-sources.json)。

保留的 ParameterParser 内含参数管理器的生成模板。已从其 ELF 数据指针恢复类型、读取器、模式管理器与选择实现，全部仅保留私有。移植封装只替换头文件名、提供基本平台类型和字符串函数，并用通用模块对象保存 name/UID/mode；没有解析所有 IQ payload，也没有启动 Android 算法服务。实际 `GetModule` 和模式表读取代码未改。初次环境缺 pyelftools 后改用标准库 ELF 段读取，不安装额外依赖；模板的无意义最小长度断言也已删除。

独立 Python 读取原 BIN 的 v1.1 模式节点和每个模块真实 ModeId，保留分组、父子和默认回退顺序。五份 BIN 的全部不同节点上下文加实际模式/用途，共 3,584 项、七类模块选择与原管理器零差。实际 BIN 没有 v2 link，不把未覆盖格式算通过；只按完整目录中等值表猜 UID 的歧义由真实 ModeId 消除。[模式结果](mode-selection-validation.json)。

普通上下文的关键选择为：

| 传感器／原厂模式 | Metering | Arbitration | LSC／CCM／MWB |
| --- | --- | --- | --- |
| Sunny GW1 mode2，4608×3456 | 106 | 110 | 25／37／117 |
| Sunny GW1 mode4，4608×2592 | 106 | 190 | 25／37／117 |
| IMX471 mode1，2304×1728 Preview | 139 | 144 | 25／37／117 |
| IMX471 mode1，2304×1728 Video | 139 | 441 | 25／37／117 |
| IMX319 mode0／2；S5K3M5 mode0／3 | 106 | 110 | 25／37／117 |

主摄使用 342 已在保留两方案内对应的 Sunny 来源。几何依据复用 321/323/324 的原厂模式、驱动寄存器与裁剪/binning 分层，不重新读 EEPROM 或扫描 I²C。这里是原索引加明确上下文的选择证明，没有观察本机原 Android HAL 的运行元数据，也未认证 manufacturer EEPROM ID，不能扩展为所有场景的自动识别。

`CAECModArbitration::UtilGetExpTableID(AECAlgoOperationModeType)` 的完整指令区间 `0x27c30..0x27e78` 经现有 Unicorn 环境运行，使用真实曝光表数量/非空 knee 信息，虚拟 custom-table 查询由封装提供。14 个模式/用途的 Streaming 均返回 0；诊断 custom override 返回 100。没有把 flash/fast/aggressive/snapshot 其它分支算完成。[原指令结果](streaming-table-validation.json)。

前摄选择的 Arbitration 根和 sensitivity correction factor 确实与旧 Default 不同，但已有 lux 路径在关闭灵敏度补偿时不读取该字段。十个已有模式/用途的实际参与计算参数全部等价，WB、LSC、CCM 所选根也与 341/342 实测配置相同，因此复用已有取流证据，没有重复采集。前摄 ExposureTable 的其它 knee 不同，未来完整自动曝光编程必须使用正确根，不能据 anchor 相同就继续绑定 Default。

新私有 Preview/Video 配置从现行 r22 默认 YAML 合并已验证校准字段，按真实 `match` 保留已有行为，仅对已对应模式加入所选根的配置；没有 YAML alias。前摄 1928×1088 为现有上游裁剪，缺原厂模式对应，保留原 generic 配置。广角/长焦全尺寸虽然有模式树选择，但本轮未凭空添加缺少的完整 IQ mode profile。[配置结果](bound-profile-validation.json)。

后续优先用现有 IPA 标准配置查找路径部署可回退的本机私有校准基线，核对默认加载、GStreamer/PipeWire 和相关模式；这不需要重编未改内核或框架。当前 r27 构建的系统配置根为 `/etc/libcamera`，数据根为 `/usr/share/libcamera`，应继续核实实际查找优先级及服务环境。私有配置在输出目录 kernel343/profiles，不放公共包。随后继续原厂 knee 曝光编程、其余场景/裁剪模式，以及正常照明光学、几何同步和连续 AF；完整目标未完成。
