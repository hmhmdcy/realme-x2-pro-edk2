# 236：后摄候选实际部署、live OF 修正与 IMX319 实际 ID

2026-10-16。本轮完成一次受控bootloader切换、只刷235 boot一次及一次fastboot reboot。建立236新启动身份后，发现并修正实验供电子驱动拒绝真实OF合成`name`的问题；仅重载未绑定的lab模块，取得真实I²C `0x0016→0x0319`回复及正常自动挂起。libcamera现能列出前摄和IMX319。**尚未采集后摄RAW/RGB，不把probe、列表或ID当出帧。** 全外设goal保持active。

用户另要求检索realme/类似机型的Linux相机和GNSS方案，本轮重新搜索并核对公开源与实测记录，见[具体仓库、补丁及适用边界](RELATED-LINUX-SOLUTIONS.md)。

## 实际过程和限制

- 新鲜236基线核当前233启动身份、775ko/789文件、用户态/包/分区原清单、实际旧MFD加载note及P/Q/provider、三DSP/SensorProxy。9份精确路径工具上传并核hash和语法；保持restart页长4096及物理寄存器代码不变。[基线](baseline-validation.json)、[工具](tools-validation.json)、[改编核验](transition-source-validation.json)
- quiesce单一worker终态0：GUI/DRM、相机端点和三个DSP停机；运行P/Q/provider保留，taint0。只发送一次Linux→bootloader请求，最终console receipt未完整返回；随后fresh fastboot身份、产品及分区几何核验成功，再只刷锁定235 boot一次并reboot一次。没有因收据截断重发切换。[清理](quiesce-validation.json)、[刷写](flash-validation.json)
- 新启动236通过严格原SSH密钥及不同boot身份核对，boot235分区、logdump/其它既有分区、用户态、模块和加载note核对已执行。前摄因新增CCI0改为9-0010，后摄为7-0010；旧guard233及旧固定设备号不可复用。
- **首个原生observer失败，exit1保留。** lab模块已加载但未绑定，无P两路rdev、后摄deferred probe。日志为lab probe `-22`；本机OF实际含`name`，Linux `drivers/of/fdt.c`在unflatten时补入该属性，而235白名单未接受。失败发生在claimed/寄存器审计/cleanupaction/rdev注册之前，尚未启动后摄供电。这个真实内核API差异未被原host回调模型覆盖，不把首次部署写成通过。
- 最小修正只在LDO属性校验中接受长度5、非NULL、内容完整匹配`ldo1/ldo4`含NUL的`name`。其它未知属性继续拒绝，mask/电压/VIN/故障生命周期/独立P复位及Q策略不改；原465例覆盖的power回调逐字相同。[修正](pm8008-live-of-name.patch)、[源核对](lab-fix-source-validation.json)
- 实际`validate_dt`函数带live OF元数据的79例ASan/UBSan通过，覆盖缺失/错误name、长度/NUL/NULL、未知属性/输出、voltage及node引用回收；旧拒绝name、忽略name值、放宽未知属性三个负对照均失败。[测试](live-of-dt-validation.json)
- 仅lab新模块树内W=1零诊断、intreeY、匹配183 ABI且导入符号存在；MFD/shared header布局保持。canonical after228、原Q源/对象及全局构建元数据恢复。[构建](lab-fix-build-validation.json)
- 同一236启动内，在严格核对旧lab未绑定/ref0、无P rdev、后摄未绑定后，只卸该lab模块、原子更新其文件/depmod并加载一次。P/Q/provider/MFD均保留，Q七路状态/电压逐项保持。新绑定自动触发后摄deferred probe，观察worker和独立I²C trace在modprobe前已启动。[原生修正结果](lab-fix-native-validation.json)
- trace只记录adapter7、addr0x10、ID消息索引/长度/方向；未按PID过滤，以覆盖deferred worker。实际三条顺序为地址`[00-16]`、读请求、完成回复`[03-19]`。各CPU丢失/overrun0、实例已删除。该值为传感器型号ID，不是设备私人标识。[ID证据](id-trace-validation.json)
- IMX319成功绑定并自动挂起；L1P=1.104V、L4P=2.8V的寄存器电压读值正确，两路state disabled/users0，MCLK1/2 enable0，前摄仍休眠。读值不是万用表测量，GPIO/时钟也不能称物理频率测量。
- `cam -l`成功列出前摄和IMX319，media graph中两颗真实sensor都存在，taint/fault0。[枚举](camera-enumeration-validation.json)。没有请求帧、保存照片或加照明。
- 最终r2检查通过当前分区、789文件、包/用户态/config、默认与加载note、两sensor/CCI/CAMSS休眠、四相机rail关、MCLK关、三DSP/SensorProxy、Wi-Fi/chrony及GNSS空闲。[最终快照](final-health-validation.json)

首次最终检查在“蓝牙仍应关闭且无连接”的假设处退出。只读复查实际为Powered=true、Discovering=false、有1连接，来源未判定；本轮没有发起配对、连接或断开。r1源/失败/部分收据保持，r2明确只记录实际蓝牙状态，不能写成“蓝牙关闭”或“连接功能已验收”。内核taint与WARN/Oops/GPU/DSP fatal/BT重组均0。

## 当前产物与回退

运行boot235 `44c6a215…`/96MiB、DTB`469e1456…`、MFD`6021a359…`/22208B、lab`5198e2bd…`/17992B、provider`2223f337…`/9744B、IMX319`176f68d7…`/36624B。前摄e49/CAMSS fae1/FastRPC2abd/BT185保持。Image183/logdump183保持，未构建整套新kernel/rootfs。

775ko/789文件的当前权威清单在设备`k236-lab-fix/module-inventory-after-private.json`和`module-tree-after.sha256`；235-stage清单中的旧lab摘要已过时。235原始组件仍冻结，236仅增加最小lab修正；完整源与构建过程可审查。当前guard为`/var/lib/samurai/k236-runtime/boot-id-private.txt`，所有此前guard失效。

235-stage保存旧232 MFD、14元数据和原loader配置，236-lab-fix/before另保存旧lab/元数据。当前lab已绑定且有IMX319消费者，不再满足本次“未绑定/ref0重载”的前提。完整回退应核当前身份、停止所有相机客户端、恢复锁定文件/元数据/config并按需要受控恢复232 boot后正常重启；不直接重放本次重载或旧quiesce脚本，不热卸有children的MFD，不触NV/校准/工厂备份。219回退另行保留。

## 下一步

为真实后摄1632×1224 RAW准备精确选相机的RAM统计探针，完成有界取流、清理和前摄回归。旧219/233探针的C++ camera selector硬编码`cci@ac4b000`，即使改sensor参数也仍选前摄，**不能用它验后摄**。新探针必须同时核Model/OF camera ID和sensor子设备；sensor/CSID图案均0，恢复全图/格式/控制及PM。222MHz link/209066666Hz阵列时钟仍为推导，须真实SOF验证。

GNSS仍无正CNR/TRACK/fix。本轮无新搜星/注入，watch自动准备UTC、数据worker0；旧226 XTRA结果不作本次启动证据。新检索得到同SoC原生四摄和厂商HAL真fix参考，尚无能直接解释本机原始零CNR的新修复；不照搬Surya unlock循环、旧Surface Duo keepalive或MEMSHARE推断。
