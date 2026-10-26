from pathlib import Path
import json,hashlib,subprocess
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel192';out=Path('/mnt/e/edk2-samurai-out/kernel192')
old=(root/'NEXT-SESSION.md').read_bytes();assert '阶段191' in old.decode()
archive=root/'archive/NEXT-SESSION-through191-2026-10-15.md';assert not archive.exists();archive.write_bytes(old);assert archive.read_bytes()==old
readme='''# 阶段192：两颗PM8008真机识别与原厂相机供电序列解码

**真机确认两颗PM8008、定位第一颗被持续复位；六份原厂相机BIN的槽位、地址、ID和供电序列已与原厂读取器逐项一致。实体传感器ID与图像仍未取得，本阶段没有部署新的相机驱动或DTB。** kernel183、189传感器组合及MM191继续运行。

## 相机电源芯片的真实状态

本机QUP SE4的`i2c@890000`对应当前Linux **i2c-1**，同总线还有两颗MAX98937。旧设备树中的i2c4/SE4不能直接当作Linux适配器4；当前Linux i2c-4是触摸。只读取原厂明确的PMIC地址，没有全总线扫描。

初始PM8150L GPIO1物理低、GPIO4物理高，均未被驱动占用。`0x04`应答、`0x08`NACK。临时申请第一根线，维持原低电平再置高，10ms后`0x08`返回与第二颗相同的身份字节`00 00 00 01 51 2c`；PMIC类型0x51/PM8008 subtype0x2c与内核定义一致。最后GPIO1恢复低，第一颗重新NACK，第二颗前后完整寄存器快照相同。GPIO4、MAX98937、SID和LDO均未写入。[真机收据](pmic-native-validation.json)

两颗的SID配置分别为2/1，对应`0x08/0x09`与`0x04/0x05`；原厂标签分别为P/Q。两颗全局CHIP_ENABLE寄存器0x0950均为1，七个LDO enable均为0。因此不能把“遗漏全局使能写入”当成本机已证实的故障。初始VSET也不是当前输出电压：LDO关闭时，读取到的是编程值。

S8C当前启用、1352000µV、用户数3，与显示共享，未切换。PM8150L L1编程值1800000µV但state unknown、用户数0，不能据此声称相机VIO已开启。本轮没有单独试开VANA或修改LDO/VSET，也没有把尚未确定的PLDO输入伪装成BOB/VPH供电。

GPIO使用本机启用的v2字符接口。flags=0的ASIS请求不指定方向/偏置/驱动，读取后检查line info不变；[Linux GPIO文档](https://docs.kernel.org/userspace-api/gpio/gpio-v2-get-line-ioctl.html)。前摄RESET GPIO12、选择GPIO29以及其它槽位RESET GPIO30/23均为输入、物理低；这些线仅ASIS读取，没有驱动改变。

## 解除BIN解析阻塞

阶段115只读提取的六份本机BIN逐个核对原SHA。格式为Parameter Parser V1.3.2，包含72字节符号表条目及64位编码的值/引用。新读取器只解析固定sensor前缀128字节、模块前缀72字节、外部名称和供电三元组，严格检查长度、引用名、槽位、可选地址/频率覆盖和边界；不解释EEPROM、校准或完整寄存器表。[读取器](decode-camera-prefix.py)

使用阶段117已固定的[CamxChi工具与XSD](https://github.com/bjzhou/CamxChi/tree/9f17f1b568626b393e785b369c5dc94543774d7a)，仅修改私人分析副本中的根长度/非目标根标记，并裁剪XSD到相同前缀。原始BIN保持不变。原厂ParameterParser在非root、256MiB地址空间、5秒CPU及输出上限下独立导出XML；六份文件的全部目标字段、上下电步骤、槽位和无覆盖状态与新读取器一致，没有达到限制或遗留进程。完整旧版XSD兼容问题仍未解决，不能称全传感器寄存器解析完成。[交叉核对](camera-prefix-validation.json)、[复现脚本](verify-camera-prefixes.py)

| 原厂模块候选 | 槽位 | 7位地址 | ID寄存器/期望值 | 上/下电步骤 |
| --- | --- | --- | --- | --- |
| qtech IMX319 | 1 | 0x10 | 0x0016 / 0x0319 | 7 / 5 |
| sunny IMX319 | 1 | 0x10 | 0x0016 / 0x0319 | 6 / 5 |
| qtech S5K3M5SX | 3 | 0x2d | 0x0000 / 0x30d5 | 8 / 7 |
| qtech S5KGW1 | 0 | 0x2d | 0x0000 / 0x0971 | 7 / 6 |
| sunny S5KGW1 | 0 | 0x10 | 0x0000 / 0x0971 | 7 / 6 |
| sunny IMX471 | 2 | 0x10 | 0x0016 / 0x0471 | 7 / 6 |

这些是本机原厂驱动包的候选配置，**不是物理探测结果，也不证明装有所有候选模块**。所有MCLK配置19.2MHz；主摄两家地址不同，不能只写死一种地址。IMX471顺序为CUSTOM_GPIO1高→RESET低→VIO→VANA→VDIG→MCLK→RESET高，各步1ms。不能把供电项中的configValue=0误当作“上电时禁用该电源”；实际电压来自槽位的regulator约束。

重新解析已验哈希的本机原厂DTBO overlay0，与OEM 19781源核对五个槽位的GPIO/CCI/电源标签。[DTBO收据](stock-camera-slots-validation.json) 前摄槽位2是CCI1 master1、RESET TLMM12、CUSTOM_GPIO1 TLMM29、MCLK2 TLMM15；VIO是PM8150L L1，VANA=L5Q 2.8V、VDIG=L2Q 1.05V。槽位3的BIN包含CUSTOM_GPIO1/2，但该stock槽位没有这两个GPIO属性；保留这个差异，不能杜撰引脚。

## 主线驱动与接入余项

当前7.3-rc6树已有`drivers/media/i2c/imx471.c`，匹配0x0016/0x0471、19.2MHz与四条DPHY lane，但config未启用、匹配表仅ACPI，现有电源模型只申请vana。需要补本机DT匹配、VIO/VDIG及选择GPIO和可回退供电流程，再接CCI/CAMSS；不能直接把现有驱动当成本机已可用。[上游合入记录](https://kernel.googlesource.com/pub/scm/linux/kernel/git/wireless/wireless/+/be1589e567aeea5d32d9dd7027501657787d3ad3)

PM8008 NLDO输入S8C有原厂来源及本机状态；另四组PLDO输入的物理父供电仍待核对。原厂生产pm8008_write_voltage()先检查请求上下限，再按8mV向上取整；抽取原函数、拦截I/O并运行ASan/UBSan，确认1.05/1.10V请求实际编程1.056/1.104V，1.8/2.8V不变。主线精确1.05/1.10V约束无可选电压，采用[1050000,1056000]/[1100000,1104000]微伏范围各只产生一个原厂等效值。[电压语义核对](pmic-voltage-contract-validation.json) 这是原厂软件编程值的证据，不是模拟电压实测；本轮没有写LDO/VSET。已确认的PMIC身份/复位状态不等于冷启动地址初始化与双芯片恢复流程通过。内部TPG126的DMA/IRQ三帧仍不能代替实体出图。

## 健康、失败记录与证据

最终仍为189第二个boot、taint0，ADSP/SLPI/modem均running；MM191程序SHA保持，PowerState3/GPS关闭；SensorProxy加速度/亮度/接近三个Has均true。相对192初始日志新增warning/oops/GPU/SLPI fatal/BT重组均0；保留整个boot已有的BT phase5重组1。[最终状态](native-health-validation.json)

初次GPIO v1 ioctl因内核未启用v1返回EINVAL，改v2后通过；首次未及时落盘的只读ID结果没有补记成功。前摄只读脚本首次把TLMM节点写成3000000，断言在申请前退出，按实测3100000改正。最终检查首次查不存在的HasCompass属性退出，后改为本项目实际HasProximity；随后修正regulator OF路径优先级，才得到最终r3。最初裁剪schema根字段名断言失败；单文件r2已实际生成嵌套XML，但顶层glob误报0文件，最终六文件验证使用rglob并逐字段比较。失败材料均保留。

手机23份证据已导出并逐成员哈希验证，SHA见[归档收据](evidence-export-validation.json)。原始日志、身份、BIN、裁剪XML和寄存器快照全部私人保存。没有PMIC寄存器数据写入、LDO/电压设置、闪存分区写入或重启。完整外设goal active，GNSS fix、蜂窝业务、BT后段重组及其它待验范围见[检查点](../../NEXT-SESSION.md)。
'''
(ref/'README.md').write_text(readme)
new=old.decode().replace('阶段191，完整外设goal active。GPS辅助发现/完整注入缺陷已修复并部署，有效fix仍无。kernel183/189传感器组合及同一boot保持；USB190故障未证明恢复，当前严格原密钥Wi-Fi管理。','阶段192，完整外设goal active。两颗PM8008真机确认，六份原厂相机供电前缀已独立交叉核对；实体出图仍无。MM191/GPS辅助修复及kernel183/189组合/同boot保持，当前Wi-Fi管理。')
row='| camera192 | P@0x08/09被GPIO1复位；临时释放识别后恢复。Q@0x04/05保持；全局使能均1/LDO均关。六BIN槽位/地址/ID/供电序列与原厂工具一致，未读实体sensor ID |\n'
new=new.replace('| 189传感器PM |',row+'| 189传感器PM |')
new=new.replace('依据：[191报告]','依据：[192相机/复位与解析](reference/kernel192/README.md)、[192健康](reference/kernel192/native-health-validation.json)、[191报告]')
new=new.replace('[190逐字快照](archive/NEXT-SESSION-through190-2026-10-15.md)保存旧部署/回退及189详细范围','[191逐字快照](archive/NEXT-SESSION-through191-2026-10-15.md)保存上一完整检查点')
new=new.replace('191 host.py沿用190私有Wi-Fi端点','192 host.py沿用190私有Wi-Fi端点')
new=new.replace('- 191主归档','- 192归档322bfbce…/23文件/逐成员验证；191主归档')
new=new.replace('实体camera PM8008四输入/冷地址/复位/chip-enable、CCI/C-PHY及真实出图待解，TPG不是实体出图。','camera192确认P/Q及复位、芯片全局使能均1。前摄slot2需GPIO29、VIO/VANA/VDIG/19.2MHz/RESET；四组PLDO父供电、冷地址、CCI及出图仍待解；IMX471主线仅ACPI/vana，TPG不是实体出图。')
assert len(new.encode())<=6500,len(new.encode());(root/'NEXT-SESSION.md').write_text(new)
p=root/'linux-port/docs/HARDWARE-STATUS.md';lines=p.read_text().splitlines()
lines[2]=lines[2].replace('阶段191。','阶段192；两颗PM8008真机确认，六份原厂相机BIN前缀独立交叉核对，实体sensor ID/出图未取得。').replace('见[191]','[192相机](../../reference/kernel192/README.md)，见[191]')
for i,line in enumerate(lines):
 if line.startswith('| 摄像头 |'):lines[i]='| 摄像头 | 内部TPG DMA/IRQ/raw10三帧；192两颗PM8008身份/第一颗复位关系真机确认，六原厂BIN的槽位/地址/ID/供电序列与原厂读取器一致 | 仍未读取实体sensor ID；四组PLDO输入/冷地址初始化、IMX471 DT/电源/选择GPIO、CCI及实体DPHY/C-PHY出图、用户态/多模式待验；BIN候选不等于实装模块 |'
p.write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(stage=192,next_session_bytes=len(new.encode()),prior_checkpoint_sha256=hashlib.sha256(old).hexdigest(),old_checkpoint_archived_verbatim=True)))
