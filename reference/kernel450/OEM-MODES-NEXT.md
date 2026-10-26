# 非主摄下一步：复用长焦 mode3，验证 720p／1080p 正常消费者

2026-10-23，离线盘点。建议在450旧统计修复的严格回归通过后，下一轮只增加 **S5K3M5长焦、现有2104×1560原厂mode3、隔离IPA的720p／1080p GStreamer消费者**。所需原厂配置和这两种IPE几何已经存在；无需新增调校表、修改sensor/DT、增加粗级容量或重新编译。新的两尺寸长焦实机结果尚未取得。

[本轮只读检查](oem-modes-next-validation.json)由[检查器](inspect-oem-modes.py)产生：复用343模式绑定、350/351/412/426完整原厂对象和440私有配置，直接比较Preview/Video所选内容；实际450头和441几何源码仍与既有数值证据一致。重新运行保留的441宿主布局工具，核对两种输出及原尺寸长焦的容量反例；没有编译、SDK bind、SSH、部署或改生产源码。公开文件只包含尺寸、开关、指纹及布尔结论，不含原厂系数或个体数据。

## 模组和可用模式的实际边界

| 物理模组／已测身份 | 本机当前sensor profile／完整IQ模式 | 可直接复用的下一消费者 | 当前不能外推的部分 |
| --- | --- | --- | --- |
| S5KGW1主摄 | 4608×3456/mode2；4608×2592/mode4 | 主线正在验证720p/1080p | 正式440的2592节点缺DS4；候选继续用443已补齐版本 |
| IMX319广角 | 222MHz链路profile只枚举1632×1224/mode2 | 720p；若要求保持4:3画幅可用1280×960作为另案 | 源码默认profile中的3264、1920、1280模式不属于本机222MHz profile；当前不能宣称1080p无放大支持 |
| S5K3M5长焦 | 19.2MHz profile只枚举2104×1560/mode3 | **720p与1080p均可保持现有sensor模式和IQ绑定** | 默认24MHz profile的4208×3120、2104×1184不是当前可枚举模式 |
| IMX471前摄 | 2304×1728/mode1有完整IQ；1928×1088只有原generic配置 | 已绑定2304模式可先显式选择后验证消费者 | 普通16:9选择可能落到1928×1088；不能把2304的DS4/LTM/LSC直接套过去。4608全幅仍依赖remosaic |

四个已测身份来自438/439/446，不把供应商备选描述重复计为物理摄像头。115本机vendor清单另有`com.qti.sensor.ov02a1b.so`，该阶段六份sensormodule描述只覆盖上述四颗的供应商组合；**450进一步核对确认第五Shine OV02A1B完整BIN早已保存在282缓存，模式和寄存器也已恢复，不需要重新寻找原件**，见[镜头及第五模组原件盘点](LENS-SCOPE-NEXT.md)。第五2MP尚无物理检测、独立sensor驱动和共享资源验收；19781板级`cam-sensor@4`与前摄共享PHY2/MCLK2/reset12及GPIO29选择关系，不能直接占用现有前摄资源。标准mux/生命周期边界继续见[完整范围](../kernel363/REMAINING-CAMERA-SCOPE.md)。

当前维护树`source354`的精确入口：`drivers/media/i2c/s5k3m5.c:741–756,1482–1488`按实际19.2MHz选择唯一mode3；`drivers/media/i2c/imx319.c:1833–1857,2665–2676`按222MHz链路选择唯一mode2。这次没有把另一profile内的表格当成本机已支持模式。

## 长焦直接复用哪些原厂数据

现成完整配置为私有`E:/edk2-samurai-out/kernel440/factory-s5k3m5-private.yaml`，SHA256 `41cba861b491d583c685e07fdc0e97d635f8922f7132abefa15d0632d4fab0a4`；其中sensor match仍2104×1560。原始BIN是`kernel306/qtech-s5k3m5sx-tuning-private.bin`，指纹`a9059286f6acf1c5d76a1f943e9f62bf3358c019f1e0b419c24b073fec56da1b`，见[原件收据](../kernel306/factory-source-validation.json)。不需要导出或替换新的配置副本。

| 内容 | 精确保留物／选择证据 | 此次复核结论 |
| --- | --- | --- |
| 物理几何与模式 | 私有343 `bound-mode-configs-private.json`；[323模式](../kernel323/tele-mode-profile-validation.json) | 普通Preview/Video mode3；LSC原点/步长继续用已核mode3，sensor输出尺寸不改 |
| IFE DS4 | 私有426 `qtech_s5k3m5sx-ds4-selection-private.json`及`-ds4-reserves-private.json`；[解析器和原管理器](../kernel426/qtech_s5k3m5sx-ds4-extraction-validation.json) | `ds4to1v10_ife_full_dc4` UID33、PASS_FULL；Preview/Video三项系数相同，440配置逐项相等。不是DS16/显示路径 |
| GTM/TMC/LTM/Gamma | 私有432 GTM树、412/351/350 `mode-profiles-private.json`；[438导出](../kernel438/rear-profile-validation.json)、[438实际ARM64计算](../kernel438/rear-math-validation.json) | GTM21、TMC11根63、LTM42；TMC10关、TMC11/GTM/LTM开，后级CCM单位矩阵。Preview/Video的LTM/CCM、TMC、Gamma完整已选对象相同 |
| 处理几何开关 | 440配置的mask/data-collect/image-processing开关；441真实几何函数 | 三者均开，匹配441三布尔几何契约；不是仅凭模块UID相同推断 |
| 其它既有校准 | 438保留BLS、动态颜色、WB/LSC和控制时序；[446长焦71帧范围](../kernel446/README.md) | 继续使用本机既有参数，不改成另机EEPROM或为720/1080复制新的sensor match |

固定语义来源继续复用[343固定CHI模式定义](../kernel343/primary-sources.json)与[426固定schema/DS410源码](../kernel426/primary-sources.json)：CamxChi提交`9f17f1b568626b393e785b369c5dc94543774d7a`，`chi-cdk/api/chromatix/XSD/isp/ds4to1_1_0_0.xsd`及`camx/src/hwl/ispiqmodule/camxifeds410.cpp`。本机原HAL SHA`e2b1b9b…a70dde`的DS410完整指令确认读取PASS_FULL；没有改用其它代际静态默认值。

## 441几何门槛：FULL是缩放后的图像

450的`camss_vfe.cpp:443–455`把sensor输入先compose为应用输出，然后按该输出配置DS4；`:580–605`据sensor实际尺寸选择IPA配置，`:694–695`把图像节点的实际格式交给`CamssIpe::start()`。后者`:46–55,80–89`按该FULL格式计算PD10并严格读回两平面格式。没有仅允许GW1/4608输入的判断。

因此长焦案例应为 **sensor 2104×1560 → VFE FULL 1280×720或1920×1080 + 同SOF quarter PD10 → 同尺寸IPE输出**。不要把RAW sensor尺寸2104×1560当成这两案的IPE FULL。

| IPE FULL | FULL NV12字节/stride | PD10尺寸 | PD10 stride／打包slice／字节 | 原厂DC/FULL stripe mask | striping／scratch字节 |
| --- | --- | --- | --- | --- | --- |
| 1280×720 | 1382400 / 1280 | 320×180 | 1344 / 92 / 123648 | 1 / 15 | 5388 / 121008 |
| 1920×1080 | 3110400 / 1920 | 480×270 | 1920 / 136 / 261120 | 3 / 63 | 7260 / 261168 |
| 2104×1560原尺寸反例 | 不安排 | 526×390 | 2112 / 196 / **413952** | 未验收 | 超过现有粗级owner上限，不能直接入队 |

前两案的布局与[441实际通用C++头／原HAL配置](../kernel441/userspace-layout-validation.json)、[完整striping+固件prepare](../kernel441/geometry-prototype-validation.json)和[最终pass distributor/BL逐对象比较](../kernel441/native-bl-validation.json)完全相同；不是新增一套长焦专用striping。441内核IPE/m2m/VFE源码哈希及450公共PD10头哈希本次重新匹配，保留两尺寸数值证据即可。该证据依然只是几何/命令一致，不代替长焦新消费者硬件结果。

441 `camss-icp-a5-m2m.c`在格式检查阶段限定`IPE_COARSE_MAX_BYTES=262144`；1080p coarse为261120B，尚在界内。raw尺寸长焦的413952B会被拒绝。若以后确需2104×1560 FULL，须单独分析scratch/owner容量、native striping/BL及DMA分配后最小扩展，不能只放宽一个常量。本轮720p/1080p不需要这项扩展。

尺寸变化时离线入口是441的`check-userspace-layout.py`、`probe-native-geometry.py`、`check-geometry.py`和`check-native-bl.py`；这些原脚本会写各自历史目录，**不要为了追加模式直接重跑覆盖旧证据**。可在新私有输出目录复用其中原函数与已有宿主工具；当前两案已经有精确缓存，无需重建或重复完整oracle。本轮检查器仅调用保留`kernel441/layout-host`，对新反例作60字节布局核对。

另外，当前`camss-vfe.c:2113–2156`明确把compose定义为全输入缩放，宽高独立限制；pipeline没有中心16:9 crop。长焦2104×1560到720p/1080p可验证消费者/同帧双遍，但这种画幅变换不能标记为中心裁剪或正常比例视频完成。后续产品画幅需要单独恢复原厂16:9模式，或实现标准裁剪且同步修正FULL/PD10/统计坐标。保持画幅的广角1280×960是可另开的低风险消费者案，其精确1280×960 striping尚未新增oracle。

## 最小实机闭环

1. 等450主线严格回归通过、充电会话明确交回串行窗口后，用同一已通过450核心/IPA6/签名/proxy、441 build4三模块及**未改440长焦配置**。按实际camera枚举选择S5K3M5实体，复用449/450 uid10000 CapEff0隔离IPA及有界应用队列；不按易变video编号选模组。
2. 只新增隔离IPA的1280×720和1920×1080两案。复用现有`gst-sustained`的短目标和正常NULL退出，每案在bootstrap之后取得连续8个成功数学历史即可判断本轮缺口；可先将短目标设32帧。无需重跑已通过的Manager循环、主摄LTM扰动、RAW-only或取消矩阵。
3. 首帧读sensor ACTIVE G_FMT必须2104×1560；日志/格式读回同时核FULL和PD10精确等于上表、实际候选core/profile载荷、真实用户与IPA进程关系。若协商改变尺寸、PD10=false或缺stock配置，停止该案，不能以有图代替双遍通过。
4. 按实际消费者offset核对每个成功图像的同SOF FULL/PD10、实际GTM cookie/generation、WB revision、前序来源统计、成功IPE receipt和数学历史；保持失败/取消不提交，完整负回执也不能重复。GStreamer已交源端但appsink未拉取的缓冲另记。审计目标从实际case设置读取，不能沿用443固定120帧断言。
5. 正常停流后核epoch作业/资源释放、无新内核故障/残留proxy、正式载荷和桌面服务恢复；永久充电栈及交回时实际源预算保持。结果只能增加“两尺寸长焦正常消费者同帧双遍”覆盖；SOF跳号、帧率、编码录像、光学色准/清晰度、16:9画幅和长焦实际AF分别保留。

如果后续要求长焦这两尺寸的独立LTM消费因果，可从其中一案保留一份FULL/真实PD10/参数，再用442固定输入的真实→黑→白→真实四次回放。当前通用LTM硬件算法未变，首次消费者闭环不必先重复主摄既有因果矩阵。
