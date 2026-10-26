# 439：前摄原厂 IPE CCM13 与自动双遍链路

IMX471 的原厂 IPE CCM13 已进入生产 IPA 自动参数路径，并与原厂 LTM／Gamma、同 SOF 真实 PD10 和成功图像的数学历史结合。2304×1728 原生及隔离 IPA 分别交付40／43帧，共83帧、79次数学历史提交、4帧显式 bootstrap；两路末尾连续8帧 AWB 锁定。隔离路径停机后另有1份未入队的计算提案，已按失败丢弃，没有推进历史。[逐帧审计](hardware-validation.json)。

固定输入硬件回放使用实拍 SOF12 的 FULL、真实 PD10 和6008字节 IPA 参数。stock重复输出与原实拍逐字节一致；单独关闭 LTM、关闭 IPE CCM 均改变输出，证明这两个处理模块实际生效。5次回放成功，不修改输入像素。本轮不新增 DC SRAM 逐字节导出或独立 PD10 扰动验证，DC 初始化／遍次机制仍沿用430／434已有证据。

正式模块、服务和资源已恢复，新增故障0、taint0，没有永久安装。全目标仍未完成：当前预览为近距离键盘／桌面，偏暗且末端色温估计达到1500K下限；不能把 AWB 锁定当成绝对色准、噪声或清晰度验收。

## 原厂数据与处理域

复用343原模式绑定、350后级 Gamma、351 CCM13／LTM、412 TMC、426 DS4、432 GTM，以及438经原解析器与独立解码核对的前摄 BLS。只对已绑定 Preview mode1／2304×1728导出完整配置。1928×1088裁剪没有原厂模式绑定，本轮保持其原配置。

原厂前摄 IFE CCM 关闭，IPE CCM UID47 有28区域、25组不同的非单位矩阵。TMC10、TMC11和GTM均关闭，LTM／Gamma开启；本轮保持原开关，不把后摄单位矩阵桥或已开启 ADRC 套到前摄。所选 LTM 有3个 AEC 区域、TMC11有1个、Gamma有3个。UID仅属于各文件内的模块编号。[导出](export-front-profile.py)、[配置检查](front-profile-validation.json)。BLS恢复原 IFE960 U14→3840 U16和2175／2048归一化；没有重读 NV／OTP 或更改原件。

通用 CCM 数学保留 IFE 的整数偏移布局及逐级截断，增加 CCM13 的浮点偏移插值和显式 IPE13位量化。矩阵仍为有符号12位 Q(7+shift)，IPE RGB→GBR寄存器排列继续由已验证底层编码器处理。共享现有 DRC／HDR／LED／AEC／CCT 选择器，目标由调用方明确指定 IFE或IPE；没有复制前摄专用算法。[补丁](0050-camss-front-ipe-colour.patch)。

对原厂 HAL 地址0x47ebf0的完整插值函数、完整 CC13 计算及 CDM 寄存器编码执行对照。主机和 ARM64 各1164例、181584字节零差，含737个原厂区域、前摄243次插值和浮点偏移边界／随机例；旧 IFE 缓存 oracle 输出仍逐字节一致。[数学证据](colour-math-validation.json)。实际 ARM64 profile 的3组完整原树选择、浮点中间结果、量化和有效矩阵也与原厂指令零差：[原树检查](front-math-validation.json)。

## 同帧、控制与提交

色温及手动矩阵随实际 WB／ISP 参数版本冻结，再复制进有界的同帧统计观察。后续控制请求不能修改已经观察的图像。未知色温明确保持上一成功颜色状态，首次缺失则单位矩阵；不补造色温。IPE 的颜色提案随数学历史成功提交，图像失败及停机丢弃不提交。标准 ColourCorrectionMatrix 元数据从实际成功的 IPE 参数包生成。

实际 ARM64 IPA DSO 检查覆盖关闭 GTM 的真实协议语义、延迟生效的色温／手动控制、旧帧不可被未来请求污染、失败历史和重启。[模块检查](front-module-validation.json)。夹具已按前摄326.4MHz／2560／2124时序及995328直方图人口数修正，关闭 GTM 的回执不带 enabled 位。主摄 legacy、bypass、上游 GTM/TMC/LTM 和提交恢复回归也通过：[回归](ipa-validation.json)。

实拍每帧核对 GTM 实际 cookie／generation、WB版本、前序来源统计、同 SOF PD10、当前 CCT、IPE 入队与最终成功历史；前摄关闭 GTM 时观测 bank0，没有宣称本轮前摄跑过两个 bank。原生／隔离分别4／5个未重算 AWB 的锁定帧，均保持相同实际 WB。两路保存的参数包与该帧输出矩阵元数据精确对应；普通路径的完整输出又经固定输入回放验证。

## 源码、部署与后续

候选为 `/mnt/samurai-full282/libcamera439-front-colour/src/libcamera-v0.7.2`，从437复制，共9个源文件变化；补丁零 fuzz／offset重放一致，Mojom和私有IPA版本5不变。[源码](source-state.json)、[构建](build-validation.json)、[重放检查](source-validation.json)。核心库50935792字节 `32cd8d41…`，IPA8183768字节 `3f83969b…`，签名 `bd9869b2…`；proxy仍 `093df5fa…`。匹配内核434三模块，source354 HEAD仍 `9bc07e63…`，未改 SoC／板级／sensor代码。

本轮439实拍只针对前摄；主摄／广角／长焦物理证据分别保留437／438，没有冒认已经用439整合版本重验。下一步整合四摄当前配置、库与匹配模块并做发布回归，继续更多尺寸／视频、完整 legacy/manual/v2/HDR、绝对画质、第五2MP、个体光学及多摄几何／同步等[完整范围](../kernel363/REMAINING-CAMERA-SCOPE.md)。原件、系数、完整日志、ELF和照片仅存私有 `E:/edk2-samurai-out/kernel439`；预览按流的 NV12/sYCC 全范围 BT.601 解码，不改应用图像。
