# 465：长焦两尺寸消费者与原厂 mode2 增量

本机长焦原件已经包含 **4208×2368 的 mode2 全表**，不必套用另一时钟的2104×1184表。恢复这张表及其调校绑定有明确依据；CSI/link频率仍有一个未闭合语义，当前没有部署条件。本轮仅离线分析、复用保留工具，没有手机访问、SDK绑定、编译或共享源码修改。

## 本机原件与模式选择

239的A/B是同一份Qtech模组BIN的两种schema投影，不是两个物理模组。两投影的mode2完整53条写入相同，且239已用独立有界BIN解码器逐项核过；本轮当前source354的mode3表仍逐条匹配B投影。[模式收据](tele-mode-validation.json)、[原件解码边界](../kernel239/s5k3m5-crosscheck-validation.json)。

| 项目 | 当前 mode3 | 保留原厂 mode2 |
| --- | --- | --- |
| 输出 | 2104×1560，二合一 | 4208×2368，不合并 |
| 原厂 capability | NORMAL | **HFR** |
| 标称帧率 | 30 | 30 |
| LLP / FLL | 9648 / 1663 | 4848 / 3312 |
| 原厂 outputPixelClock 元数据 | 481930000 | 481930000 |
| 相对mode0活动窗口 | 全幅 | 垂直裁去上下各376像素 |
| 当前19.2MHz驱动可枚举 | 是 | 否 |

原厂标签HFR与声明30fps同时保留，不将其改写为Normal或已验60fps。mode2的4208×2368是原厂近16:9裁剪；其比例较精确16:9小约0.0422%。现有VFE compose按输入全幅独立缩放两轴；恢复mode2可消除mode3的明显4:3拉伸，仍不能宣称已实现精确等比中心crop。

[查询收据](selection-validation.json)明确固定域为 `[Default=0, Sensor=2或3, Usecase=Preview(0)或Video(2), Feature1=0, Feature2=0, Scene=0, Effect=0]`。保留BIN中129种模块tag×四上下文，共516次查询，独立v1.1节点／ModeId读取与原管理器逐项零差，四上下文全部选到同一对象。这里是恢复ParameterParser内嵌模板后编译的 `ParameterSetManager::LoadBinaryParameters/ReadSections/GetModeEntry/GetModule`；仅Generic模块载荷解析被替代以保存name、UID、ModeId，不冒充Android HAL运行时选择或再次解析全部IQ系数。模板、编译输入、可执行文件和原BIN均固定哈希，完整查询输出私存。

因此mode2可复用现有mode3的DS4 PASS_FULL、GTM、TMC11、LTM、Gamma、WB、曝光表、LSC/CCM等选定对象；这比仅看少数UID相等更强。适用域仍是上述普通显式上下文，不外推HDR、ADRC、场景、特效或运行时覆盖。

## 已准备的私有增量与唯一CSI语义缺口

[草稿生成器](prepare-mode2-draft.py)已在私有kernel465保存完整53条mode2写入表，以及在440私有配置末尾追加mode2的草稿。原mode3逐项保持；新节点仅改match/control的宽高与LLP/FLL，以及LSC映射 `source_span=(2103,1559), first_quad=(0,188), quad_step=(1,1)`。原厂LSC core/golden和本机unit完全复用，其余IQ对象也完全相等。[草稿收据](mode2-draft-validation.json)。

LSC映射沿用321/323已说明的固定CamX mode0输出参考约定：mode2比mode0的起点向下376原生像素，即188个Bayer quad，最后位置1371，上下各留188。目标HAL fullResolution赋值尚未独立复现，这个既有边界保持。草稿的481930000控制时钟及两帧控制延迟继承当前mode3策略，**不是mode2物理时序验收**。草稿未填写新的Linux link_freq，不可直接安装。

mode2/3的外部时钟字段一致，但0x0312不同；不能从相同outputPixelClock或VTPixelClock反推其实际D-PHY clock。新读固定[CamxChi参考CreateCSIPHYConfig](https://github.com/bjzhou/CamxChi/blob/9f17f1b568626b393e785b369c5dc94543774d7a/camx/src/core/camximagesensordata.cpp#L2667)会按outputPixelClock、位深和lane数计算声明dataRate。目标HAL实际实现与该版本不同：[原指令收据](csi-declaration-validation.json)核对 `SensorNode::CreateSensorSubmodules` 调用CSIPHY Configure前13条原指令，三组显式provider输入共39条，把解析对象0x28槽原值搬到packet+16，并没有这段换算。该小片段没有执行Configure、完整解析器、Android服务或硬件，也没有证明这个输入槽的完整结构来源。**最小尚缺证据是本机0x0312两取值对应的实际OP/HS clock关系及Linux link_freq单位值**。参考KMD声明字段和缓存VT元数据均不能替代它，不因此重复提取EEPROM或修改原厂PLL表。

## 下一实机与模式增量次序

1. 主线窗口条件允许时，先完成现有mode3的720p／1080p正常隔离消费者。直接复用461 core、444 IPA6／旧proxy／签名、441三模块、440长焦私有profile和449已有GStreamer客户端；每案先取32张正常消费并按实际日志核同SOF FULL/PD10、GTM、WB、前序统计与成功数学历史。不得重启449/450/461的已结束worker。精确二进制哈希、参数、几何与可选回放见[消费者计划](consumer-plan.json)；该JSON不包含执行入口。
2. 实际首帧sensor G_FMT须2104×1560；FULL分别1280×720、1920×1080，PD10分别123648、261120字节。从新媒体图和应用FD确定FULL角色，沿用463语义门槛；不固定video3或从RDI0推断。审计器在新目录显式改model、尺寸及32帧目标，不直接运行会覆盖历史结果的旧checker。
3. 若要增加**长焦自身**的LTM消费因果证明，只为720p保留一组真实FULL/PD10/6008字节参数，复用442现有capture和441 pd10-ipe做真实→黑→白→同一真实四作业。FULL／参数固定、三种输出不同、真实首尾逐字节相等，并与源图相等。普通GStreamer哈希探针自身不会保存这组三输入；不能把主摄442的因果结果改称长焦独立因果实测。
4. 并行收敛上述单一CSI语义后，才在**私有sensor候选**追加mode2完整53写入、活动crop `(0,376)/4208×2368`及每模式正确link索引。保留现有mode3与原厂初始化，不重建Image。当前461 `CameraSensorLegacy::getFormat`已优先比较宽高比，再比较面积，两个尺寸会优先选择新mode2；无需为此增加sensor专用pipeline分支。实机首帧仍必须读回实际模式并验证新控制时序、LSC坐标、FULL/PD10/统计与终态恢复。

mode3两尺寸仅增加双遍消费者覆盖；原厂mode2属于后续画幅与模式适配。两者都不代替长焦AF、正常光学色准／清晰度、编码录像或多摄几何同步验收。完整53写入、IQ系数、个体数据、日志和二进制均保留在 `E:/edk2-samurai-out/kernel465`；冻结旧阶段没有修改。
