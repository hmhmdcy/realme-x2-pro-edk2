# 304：原厂 EEPROM 的 WB／LSC 类型表与旧 XML 错位核查

2026-10-19。离线分析，未操作手机、未写EEPROM／OTP／NV，未应用本机个体校准。实机最新为[303硬件AE试验](../kernel303/README.md)，内核#298、产品仍RAW＋CPU ISP；目标active且未完成。

## 发现与重新定位

299已经明确完整EEPROM布局／校验未通过。304进一步证明其导出XML后半部分不能作为调校输入：旧XML的WB qValue=0、LSC meshHWRollOffSize=1，与同一原始模组BIN的类型表及数组不一致。原始数据仍保持，不去修改读取样本来迎合XML。

[类型表审计](audit-eeprom-layout.py)固定原厂`com.qti.sensormodule.sunny_imx319.bin` SHA256，先验证分节范围、203字根与UID引用。根据原始`lightInfo`数组长度和根中的计数定位两个区段：WB五个15字元素，LSC五个17字元素；不是沿用旧XML的根字段偏移。

WB区段表示LITTLE／INDIVIDUAL，Q值为1。LSC原始区段为221点、四通道、各通道步进5字节；每点四个低8位字节与一个共享高位字节构成packed40数据。[审计收据](eeprom-layout-validation.json)

读取并解码299保留的两份12287字节样本，五光源的WB分母均非零，共解码4420个LSC通道值。数据、序列号、样本哈希、数值及曲线均留在私人目录，没有放入设备调校包。

## 独立对照与来源

自行实现的[固定packed40 C解码器](decode-lsc.c)与类型表驱动的Python解码器采用不同表达；非对称手工向量、全零／全1边界通过。两份读回分别对照五组四通道，每组221点逐值一致。[交叉核对](lsc-crosscheck-validation.json)

公开原厂实现的[FormatWBData／FormatLSCData](https://github.com/comprehensive9/vendor_qcom_proprietary/blob/36fc163a534963a5b3af52186af5efcc63401ad2/camx/src/core/camxeepromdata.cpp)提供按mask抽取高低位、拼接及逐点地址步进的语义依据；[HWRollOffTableSize](https://github.com/comprehensive9/vendor_qcom_proprietary/blob/36fc163a534963a5b3af52186af5efcc63401ad2/camx/src/core/camxpropertydefs.h)定义221个表项。[来源锁](primary-source-validation.json)保存本轮读取的XSD／源码指纹。

这里没有证明该公开源码的完整版本恰好匹配原厂BIN。旧XML错位根因仍需进一步匹配历史schema／生成器；目前只重新定位并交叉解码WB／LSC区段，不声称203字根的全部格式已重建。

## 仍不能直接应用的部分

- 工厂checksum／有效标志、模组供应商与本机绑定仍未确认。原厂内核`cam_eeprom_check_data()`是按调用者指定起点／长度、每页首字节求和的工厂检查入口，不是已经找到的WB／LSC存储块校验算法；不把它当完整校验通过。
- 221点不独立证明17×13的行列方向、裁剪、镜像或传感器模式映射。17×13仅为待验证候选几何；尚未确认亮暗场含义、表值尺度及与Chromatix golden表的合成方式。
- WB原始比值不等于当前场景的白平衡增益，不能直接替换303临时WB。完整AWB还缺RGB统计与算法／色温选择，Y BHIST不足以完成它。
- AF／PDAF／其它区段、校验、暗场、颜色矩阵和完整画质均待继续；两读一致及两个解码器一致不等于数据本身已完成工厂校验。

私人根`E:/edk2-samurai-out/kernel304`，原始BIN和两份读回仍在原位置；本轮没有修改内核、板级DT、libcamera源码或任何已安装包。
