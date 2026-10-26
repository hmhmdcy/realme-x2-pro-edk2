# 487：三 sensor 静态属性候选与四摄 rotation 缺口

已生成只改 libcamera sensor 属性库的最小候选，未编译、安装或访问设备。它补 S5KGW1、IMX319、S5K3M5 的 UnitCellSize／已知 test-pattern 映射；IMX471 原条目保持。旧440／473及481–484文件、驱动、模式表、profile、DT和共享源码未改。

| Linux model | 原厂 pixelSize | UnitCellSize（nm） | 新增标准 test-pattern → V4L2 menu index |
|---|---:|---:|---|
| s5kgw1 | 0.8µm | 800×800 | Off→0，ColorBars→1 |
| imx319 | 1.4µm | 1400×1400 | Off／Solid／Bars／Fade／PN9→0／1／2／3／4 |
| s5k3m5 | 1.0µm | 1000×1000 | Off／Solid／Bars／Fade／PN9→0／1／2／3／4 |
| imx471 | 1.0µm | 1000×1000 | 已有条目，不修改 |

这些值来自本机保存的原厂 BIN，不由分辨率、binning倍率或近型号推导。IMX319 的 Qtech／Sunny 两份均为1.4µm；本次选取的缓存权威同型号资料没有发现冲突，未进行新联网搜索。3M5与471还交叉核了326保存的当前描述。这里复用原厂模型的单个pixelSize及其在两个轴上的实际用途，不声称做了光学尺寸计量或获得完整厂商规格认证。

语义不仅依赖“三个看似合理的浮点位置”：固定本机 HAL `e2b1b9b6…a70dde` 的根加载器片段 `0x191114→0x19120c`，实际把序列化qword92…94加载为native600／608／616；同一 HAL 的消费者 `0x4f4e08→0x4f4e84` 从native600读double，转float保存pixel-size，并除1000、分别乘两个阵列方向，保存物理尺寸。原生片段使用故意不同的1000×2000 provider轴，证明同一标量在两方向的用途；8份实际描述加1份distinct sentinel全部一致，消费者各执行31条真实指令，无外部调用。缓存 XSD 的 SensorProperty 尾三字段为 pixelSize(double、µm)／cropFactor(double)／sensingMethod，参考 GetStaticCapabilities／PopulateLensPoseInformation 源码也对应相同用法。没有将较新完整schema的兼容性或相邻delay布局宣称为已证明。[字段与消费者收据](metadata-evidence-validation.json)，完整原件指纹、OEM角度及精简指令只存私有487。

图案映射依据当前驱动的V4L2菜单，不把寄存器值当菜单索引。GW1 的 Color Bars 菜单index1才写寄存器value2；“Shade Color Bars”index2尚没有可靠的标准语义映射，本候选不将它猜作FadeToGray。其它三颗的五项菜单明确对应标准名称；IMX471原映射逐字节保持。这是源码/API映射检查，没有启动图案或新增实机图案验收。

三个新条目的 `sensorDelays` 均空，保留现有 CameraSensorLegacy 的未验证默认回退；不把479某模式的及时写入+2响应填成整个sensor的全局delay。CAMSS既有调校和延迟策略不动。候选路径为私有 `kernel487/candidate/src/libcamera/sensor/camera_sensor_properties.cpp`，SHA `51a62ca0139a9ee3639c406ec9a2e67b1330766673634d10ce4addfc3cd0080a`；[源码补丁](0001-camera-sensor-add-samurai-model-properties.patch)零fuzz／offset应用，移除三个新条目后完全恢复原源。[source/fixture收据](source-validation.json)。

四摄 rotation 警告另有原因：哈希匹配363已部署原件的保留DTB中，后摄orientation1、前摄orientation0均存在，四节点均没有rotation；四驱动已经通过标准fwnode parser／control helper接入。CameraSensorLegacy未收到 `V4L2_CID_CAMERA_SENSOR_ROTATION` 时才回退0度。正确接入层是本机sensor节点的标准DT属性，不是libcamera的sensor型号属性表或强制默认值。

本机BIN的命名OEM mount角度已保存，但cached schema分roll／pitch／yaw轴且含无效360哨兵；尚缺从本机原HAL静态方向到Linux mounting-rotation参考系的可靠变换依据。266已明确拒绝直接等同，487沿用该边界；没有复制Hotdog的rotation，也不写 `rotation=0` 只为消警告。当前不生成rotation patch。下一最小缺口是闭合该参考系／方向关系，再单独补DT并验证实际属性和图像方向；本次零设备工作不新增光学或遮光要求。

复核入口：`inspect-properties.py`运行本地有界真实指令片段；`prepare-candidate.py`只在尚不存在的私有目录生成源候选并核菜单／保留DTB，不触发SDK或构建。当前两份验证已通过，候选尚未编译和部署。
