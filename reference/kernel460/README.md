# 460：匹配 ODM AF override 的有限原指令核对

**本次取得的默认ODM配置会走到HAL边界override分支，但不会改变453长焦条件候选的数值。**实际选定 `Mode[0]`／`Mode[1]` 后，上下界、initial code、codePerStep及全部个体步表项均与原453候选相等；没有改写该候选、原nominal文件、原厂配置或驱动。checksum接受、static sag gate、实时姿态和光学安全继续未验，不升级为可部署AF配置。

[脱敏收据](override-validation.json)只包含事实、计数和公开代码范围。库、1121字节配置、系数、端点、个体表、完整指令轨迹及失败记录保留 `E:/edk2-samurai-out/kernel460/`。453／459保持冻结。整个460只离线执行有限AArch64范围，没有手机／SSH／SDK、编译、网络或部署；没有重采EEPROM。

## 来源与默认加载顺序

本次输入沿主线只读采集收据复核：281 HAL完整SHA `e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde`匹配；ODM `lib64/libhwconfigurationutil.so` 为109784字节，SHA `9b317c9e3154929964aef1cca37b79fda00f7201c119d5f4cf9656f5c1917548`；配置为1121字节，SHA `4d73f1ad3216bc9338e9113cd23d2b1ea68403cee3ab0b3c9fe718aa3f4e37f0`。保留库及settings的只读debugfs来源证明；未挂载ODM、未在手机执行OEM代码或写文件。

`HWConfigurationUtil`默认单例的构造指令 `0x15e68` 给 `KeyFile::Create` 传入硬编码 `/odm/etc/camera/CameraHWConfiguration.config`；后者实际调用 `KeyFileLoadFromFile`，唯一 `fopen` 尝试使用 `r`。实际离线成功和缺文件两个有限案例均只有这一个路径；缺文件返回空KeyFile，公开GetKeyCount返回0，未尝试 `/vendor` 或 `/data` 回退。这是默认单例内的顺序，通用KeyFile类接受调用方自传路径的能力不等于默认单例存在第二优先来源。

没有执行Android linker namespace、实际文件系统覆盖或真实HAL进程单例生命周期，不能把“当前保存的ODM默认文件”写成所有运行环境永远不被覆盖。原件由匹配HAL门槛接纳；本结论仍绑定本次保存的默认库／文件。

## 原库解析和接口

[native-config.py](native-config.py)加载实际ELF PT_LOAD，并恢复Android APS2／RELR／PLT重定位。执行原构造加载段、KeyFile::Create／LoadFromFile、LineParser、KeyFileKeyValuePair解析、HashTable查找和公开getter。getter的单例存储按真实布局绑定到已加载对象；构造函数 `0x15eb0` 后的诊断dump／统计遍历未执行。

当前文件实际含 `OemCamActuatorSettingMap` 下四个键 `Mode[0]` 至 `Mode[3]`。分隔符是分号，含行尾注释；不能以空白split自行接受。原库执行得到组键数4，GetValuesCount针对 `Mode[0]` 为4；四个locale均成功返回四整数。Locale字符串由原库组合成 `Mode[n]` 后查找；不存在locale失败，缺key计数0，短输出按原指令min(count,capacity)写入且canary不变。独立文本读取只作逐项对照，不提供原库getter返回值。

这一组执行33261条原ELF指令。`std::getline` 字节流、filebuf close、libc++字符串／locale／分配／精确类型cast有明确的有界provider；整数转换使用宿主libc `strtol`，目标库继续执行后缀检查和int32存储。文件provider只提供已验证的1121字节内存，不通过OEM stdio访问或写宿主文件。两个内联标准C++ helper由provider接管，因此不是完整libc++／codecvt或Android运行时验收。

初次尝试错误假定 `fopen` 为rb，随后补齐getloc provider；刻意简化的codecvt环境还在close触发abort。三次均未计入最终通过，私存原因；最终显式提供标准filebuf close，不把这部分说成原生运行时已验。

## 连到实际 HAL 前置分支

[inspect-override.py](inspect-override.py)按AST复用453的原HAL描述parser／EEPROM formatter函数，所有输出重定向到460私有目录，不导入453顶层动作或写453。仍使用326现存的同两份EEPROM缓存；执行器对象也由原native parser恢复，确认当前长焦为type0、10bit。

从HAL `0x4f7e44` 执行到 `0x4f89cc`，覆盖原先尚未核实的前置查询和后续全部margin／clip／建表指令，5487条指令。本次HAL确实要求该组恰好四键，查询 `Mode[0]` 的值数，以原格式化函数生成locale `0`／`1`，经原库公开接口取得两行并实际执行边界算式。API桥只跨两个仿真地址空间搬运原库结果，没有以自写配置parser代替查询。

边界算法为每行四整数对应的 `a × (b × 2^(c + bitWidth) + d)`；type0选择0／1，type1选择2／3，但本轮只对453已经绑定的长焦type0／10bit作表项结论。不能从type0的等价关系推断所有执行器或其它模式。

进入margin核心时的两边界与453先前条件输入逐字相等，最终initial code、float32 codePerStep及全部表项也逐项相等。因此本次补证消除了“这份匹配默认表是否会改变该候选clip输入”的数值不确定性，**无需重算或改写原453表**；没有形成正式参数文件。原453源码、收据、条件候选及已保存nominal候选SHA在回放前后保持。

## 复现与剩余范围

按顺序运行 `python3 -B reference/kernel460/native-config.py`、`inspect-override.py`、`finalize.py`。第二脚本在WSL相关读取前先经449 `mounted_build()`，没有SDK或生产源码写入。[finalize.py](finalize.py)只读私有原始结果，核执行范围、分支、所有表项和冻结文件后生成脱敏收据。

保留以下未验：本机工厂AF checksum／接受函数、物理供应商认证、static runtime-sag gate、实时gravity／姿态、真实HAL进程选择的当前文件、光学响应／FoM、实际搜索与稳定时间／电气安全。原453数学与实际默认配置分支的软件对等不替代这些条件；`deployable=false`、`applied=false`。
