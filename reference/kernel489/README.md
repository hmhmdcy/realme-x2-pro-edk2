# 489：安装路径、原厂静态属性和总线格式的增量 core

候选已增量构建并通过 ARM64 SDK 验证；未安装到手机，当前正式基线仍为 [484 的 r33/r28](../kernel484/README.md)。本轮没有访问手机、重启或刷写，调校数据、IPA6、签名、proxy、base、驱动和私有 profile 保持原字节。

基于473现有源码/构建目录复制575,330,273字节到独立候选，只合入两个源文件：[487](../kernel487/README.md)的三个 sensor 原厂 UnitCellSize／已知菜单映射，以及[488](../kernel488/README.md)的 `0x2027` 15 bpp/YUV 条目。两个补丁零fuzz／offset应用，473父源码、父构建和原 core 保留；IPA系数、协议、PD10内存布局及双遍时序均未改。sensorDelays、DT rotation 未猜填。[source-state.json](source-state.json)记录来源和哈希。

[build-validation.json](build-validation.json)：只请求 core 目标，实际编译两个受影响对象、执行未改变内容的版本生成检查并链接，71.916秒完成；没有重编IPA、proxy、base或整套Image/rootfs。按[485](../kernel485/README.md)复用Meson安装时RUNPATH处理后，core为 `b345af8b1430718b8fbcbbfde95916d66312bf0fc0e1b237edfb177332818bdd`，51,262,920字节。归一化前后只允许动态表的RUNPATH项和原路径字符串变化，其余字节相同。

[SDK验证](sdk-validation.json)使用私有 overlay，放入已核对的57个现有r33/r28载荷文件、原主摄私有profile，运行库仅替换这个新core；配置查找用例另在overlay内使用合成的个人/系统marker配置。没有执行APK安装或改底层SDK的DB/world。实际ARM64运行结果：

- 默认loader、`cam --help`及base/core/GStreamer/V4L2兼容层/CAMSS IPA的RTLD_NOW加载通过。
- UID10000实际调用新core的原函数，四sensor属性可读，`0x2027`为YUV/15 bpp，build/source路径均为空；未进入误判的build分支。
- 新core公钥实际验证原CAMSS IPA6及原签名通过。原主摄 `/etc` profile 和系统 `camss_ipa_proxy` 路径解析正确；这里只解析/验签，没有执行worker、启动CameraManager或运行调校数学。
- 合成私有HOME下，实际GlobalConfiguration验证个人配置优先、缺失时系统回退、权限拒绝时报错且不读取系统配置。最后一例仍有默认空配置version1，这是构造器159–161行的原行为。NSS/目录是SDK测试fixture，不能冒充手机真实用户配置或486新launcher的实机验证。

失败均保留：[r1](sdk-r1-validation.json)测试编译漏掉项目生成的config.h，未暴露条件声明的pubKey；修的是测试编译参数。[r2](sdk-r2-validation.json)加载、属性、签名和个人/系统两例已通过，但把权限拒绝后的默认version错误预期为0，断言失败。[r3](sdk-r3-validation.json)只将该预期改为原实现的1并补跑权限例；核对旧测试源码仅这一断言变化及同core字节后，复用r2已过项和原日志，不重复无关验证。生产源码和候选ELF未因这两次失败改动。

SDK bind/overlay已全部卸载，编译临时文件移除，SDK DB/world保持；窗口已归还充电会话。完整失败/成功日志、overlay上层和候选ELF留私有489。公开目录只含工具和脱敏收据。

下一步是以新包版本准备可回退候选，待充电会话明确归还手机后，按新的boot/guard/transport及481 formal-expected核对当前r33/r28，再用486启动器做定向默认路径采集。需要确认本轮缺失属性/总线格式/build-tree提示消失，保持四摄输出、同帧PD10配对与实际LTM消费。441/442/469/474已通过的未变数学范围继续复用；本轮SDK检查不扩成实机、光学、长稳或完整摄像头目标完成的结论。
