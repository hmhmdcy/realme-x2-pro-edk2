# 291：两颗实体传感器接入硬件FULL及独立RAW色彩对照

2026-10-19。291（2026-10-19）：现机仍#290/778模块，广角RGGB与长焦GRBG已经真实CSI→CSID175 IPP→VFE175 FULL取得硬件NV12；传感器内部图案分别对照独立RDI RAW，红蓝及色彩转换通过。六组共108帧，结束后四摄18段229帧回归通过。广角实景RAW近黑电平，正常实景/黑电平校正/统计参数/IPA与完整画质仍未完成。

本轮属于实测进展，不新增内核或用户态产品补丁，不刷写、不重启、不替换模块/包。部署仍为290提交15c8639d8badf5d4146bfd1b2c2fcb2460a137e5／samurai-full-route290，boot276及DT保持。[部署来源](../kernel290/README.md)、[当前预检](runtime-preflight-validation.json)

## 复用既有方案及分层

继续采用已核对的[IFE标准MC/V4L2测试方案](https://github.com/0xB0D/ife-tests)及290标准TPG工具框架，扩展为实体sensor→CSIPHY→CSID0 IPP→VFE0 PIX FULL。MC实体与major/minor发现节点；sensor原模式、原生曝光/增益控件、标准selection设置缩放，不用MMIO、私有HAL或CPU ISP补色。

板级DT/固件和公共SoC驱动保持；本轮验证290已部署驱动是否能处理实际CSI输入。工具只用于开发验收，不替代未来libcamera pipeline/IPA。启动身份严格沿用290原SSH密钥和boot guard；不操作OTP/NV/工厂校准。

## 广角实体输入：出帧与光学证据分开

IMX319实际1632×1224 RGGB10，目标NV12为320×240。显式设置VFE sink COMPOSE，避免只改video格式而未设置缩放。所有相关pad格式、VFE compose/crop、sensor曝光/增益/图案及CSID图案先保存，结束逐项读回；MC图逐字恢复，供电/时钟正常回收。[标准工具及构建](physical-tool-validation.json)

sensor/CSID图案均关闭、增益码512，曝光500→3000→500行，共18帧NV12连续序号/时间戳通过。但保存图像Y约70.94/70.97/70.94、几乎均匀，不能视为正常光学成像。[实际采集](physical-capture-validation.json)

同模式、同控件的RDI RAW参考也为18帧，按有效行解包MIPI RAW10，三档后段均值约64.049/64.177/64.047，全部像素低于100。说明当前弱响应在原始输入中已存在，尚不能归因于FULL处理丢失细节；RAW64经过尚无黑电平校正的sRGB曲线约为Y71，与NV12一致。这是数据域解释，不是把单场景64写为固定校准。[RDI参考](raw-capture-validation.json)、[像素分析](physical-pixel-validation.json)

已询问用户确认后摄正常照明/无遮挡；未将摆位或答复作为统计/参数等独立适配的前置条件，普通实景画质仍待验证。

## 传感器图案经真实CSI验证两种Bayer及红蓝

IMX319使用标准sensor test_pattern=2，CSID内部TPG保持0。分别RDI与PIX各18帧，原始四CFA通道表明有效区域有白/黄/青/绿，R与B可独立区分。硬件NV12与独立RAW经标准601 full-range期望的最大通道误差1.235以内。[RAW](pattern-raw-capture-validation.json)、[PIX](pattern-pix-capture-validation.json)、[独立分析](physical-pixel-validation.json)

S5K3M5使用实际2104×1560 GRBG10、原生增益码64及150/1200/150行曝光，sensor图案2、CSID图案0。RDI与PIX各18帧，独立RAW确认白黄青绿品红红蓝黑八色，硬件NV12逐色匹配，最大通道误差同样1.235以内。[原生控件](tele-controls-validation.json)、[RAW](tele-pattern-raw-capture-validation.json)、[PIX](tele-pattern-pix-capture-validation.json)、[像素](tele-pixel-validation.json)。私人预览已核看，像素不写公共仓库。

六组总计108帧标准采集均正常结束，graph/格式/selection/控件恢复、资源回收，无新增所查fault/taint。RAW参考因CPU遍历统计出现跳序，保存帧序号仍递增；不称完整无丢帧30fps验收。图案两端为0/1023，不能据此验收中间亮度曲线、噪声、AWB、光学几何或完整缩放质量。证据范围是两种模式、标准选择的尺寸及静态垂直色块，不能推广全部sensor/模式。

长焦RAW工具INPUT行的output标签仍写1632x1224，属于复制工具时的日志标签遗漏；实际输入检查/S_FMT/FORMAT为2104×1560、stride2640、bytes4118400，解包与统计也按这些实际尺寸。保留原工具/哈希/输出，未掩盖或用标签推断分辨率。

## 回归、最终状态与下一步

后续四摄标准cam独立进程18段229帧通过，包括SIGINT和同主摄重开；仍为既有RAW＋CPU SoftwareIsp，不是libcamera已改走硬件ISP。[回归](four-camera-regression-validation.json)

全部778模块、旧288778项和旧k132776项、50包载荷及961包保持；五sensor/lens、双CCI/CAMSS休眠，九rails及共享IO关闭、MCLK/CCI clocks0，fault0/taint0/pstore空，桌面原进程及三DSP/SensorProxy正常。[最终健康](final-health-validation.json)

下一步应接真实硬件参数/统计和帧级对应。175现有WB参数后端仅接受零offset，尚无实际注册的参数/统计节点；不能将头文件或内部回调算成用户态接口已可用。优先复用既有公共typed params框架，按能力注册175参数节点并实测WB，研究可正确表达黑电平的硬件模块，再接原厂175统计协议及libcamera pipeline/IPA。不要为灰图在应用补gamma或把本机黑电平硬编码进SoC驱动。

主/前摄硬件成像、正常实景/黑电平/颜色/阴影噪声、AF加速/Continuous/距离标定、GUI录像及统一rootfs/升级回归仍开放。上游接收、ignore_unused收敛、历史GPU默认故障和modem watchdog均未完成，目标保持active。[检查点](../../NEXT-SESSION.md)
