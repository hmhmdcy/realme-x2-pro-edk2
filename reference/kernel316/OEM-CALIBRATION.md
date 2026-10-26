# 本机原厂 HAL 的 EEPROM 数据路径

2026-10-19。本轮从原厂vendor分区只读取得camera.qcom.so及其同名前缀依赖，仅离线分析，从未加载或执行原厂代码。只读挂载带noload／noexec并已卸载；个体分析使用299已保留的IMX319读回，没有新读写EEPROM、OTP或NV。

camera.qcom.so SHA256 `e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde`。该库已剥离内部符号；通过原厂`fx319aa_imx319`字符串、AArch64 ADRP／ADD交叉引用、unwind FDE函数边界及函数日志字符串定位，而不是把objdump显示的最近导出符号当真实函数名。

本机分支在0x503290～0x5032d8比较EEPROM名称fx319aa_imx319（也接受imx319_gt24p128c2csli），角色参数为2。对应数据路径：

| 数据 | EEPROM位置／长度 | 原厂依据 |
| --- | --- | --- |
| 序列号 | 0xb0，17字节 | 0x504b18的DumpSNData：向量读取16字节，再读取0xc0第17字节 |
| 畸变数据 | 0x1876，3441字节；有效标志0x25e7 | 调用0x504648 DumpDistortionData，先检查标志字节等于1，再复制0xd71字节到原厂persist文件 |
| 广角AE同步数据 | 0x2d00，36字节 | 调用0x505f18 DumpAEsyncData，首字节为0xff时拒绝；0x504f30 CalculateAESync还做数值有效性检查 |
| 通用模块数据读取 | 由请求结构指定起点，1689字节 | 0x505cc8 ReadModuledata，本身只做拷贝，不能视作校验器 |

现有单位样本中的畸变标志为有效、序列号非空白，AE同步区通过首字节哨兵检查。[机器记录](oem-calibration-block-validation.json)。实际数据、序列号、块指纹及反汇编保存在私有目录，未放进调校包；未修改persist文件，也未尝试复现原厂写文件行为。

进一步从CalculateAESync的实际字节算术确认：AE记录偏移4的3个ASCII十进制位为平均亮度，偏移8的3位为增益×100，偏移12的5位为曝光参考×1000。广角记录的这些字段都是合法非零数字，实际数值仍只留私有目录。[字段解码](ae-sync-decode-validation.json)。原厂输出slave／master平均亮度比，并分别保存两者的增益和曝光参考；目前缺少主摄对应单位参考，曝光换算后的物理单位亦未确认，尚未应用同步系数。

这些结果明确了个体绑定、多摄畸变和曝光同步的原厂数据来源，但尚未解码畸变模型／内参及AE记录的完整布局。有效标志和哨兵不是CRC，不能据此认定304的WB／LSC完成工厂校验，不能直接应用个体值。

已优先核对[通用CamX EEPROM源码](https://github.com/comprehensive9/vendor_qcom_proprietary/blob/36fc163a534963a5b3af52186af5efcc63401ad2/camx/src/core/camxeepromdata.cpp)：它有EEPROM格式插件接口，但该已知版本不包含本机DumpDistortionData／CalculateAESync的OPLUS分支。检索没有找到可直接匹配这两个函数的公开实现，因此继续依赖本机HAL证据，不套用其它机型的畸变表或golden数据。完整WB／LSC校验、模式映射与个体应用仍待完成。
