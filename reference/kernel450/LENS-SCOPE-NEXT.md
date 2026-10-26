# 其它镜头与第五模组：已定位可接入的原厂数据

2026-10-23。只做离线原件解析、固定源码审查及独立 XML 交叉核对；未访问手机／SDK、未编译、未改生产树或部署。结果见[解析收据](lens-scope-validation.json)、[解析器](inspect-lens-scope.py)；可继续构建的 BU64253 草稿见[453](../kernel453/README.md)。

446 的三路 `lens_focus_active=false` 原因不同。**IMX319 和 S5K3M5SX 均有原厂 BU64253 VCM 描述，当前缺标准 lens 驱动、供电及 `lens-focus` 绑定；IMX471 原厂描述没有 actuator，符合固定焦点配置。**不能把三者全部当作固定焦点，也不能从主摄一次 Focused 推导其它镜头已支持 AF。

| 模组 | 原厂执行器与地址 | 原厂板级连接 | 当前缺口 |
| --- | --- | --- | --- |
| IMX319 Sunny／Qtech 文件 | `imx319_bu64253`，8-bit `0x18`→7-bit `0x0c`，10-bit VCM | CCI0/master1；Q侧 L6，2.8V | source354 无 BU64253 驱动；`imx319.dtsi` 无 lens／`lens-focus`，Q侧 L6 尚未声明 |
| Qtech S5K3M5SX | `s5k3m5sx_bu64253`，同为 `0x0c`／10-bit VCM | CCI1/master0；P侧 L3，2.8V | 同样缺驱动与 lens／`lens-focus`，P侧 L3 尚未声明 |
| Sunny IMX471 | actuatorName 为空，无 actuatorDriver | 原厂 slot2 的 actuator-src 已注释 | 保留固定焦点身份；不凭 sensor 名称追加 VCM |

原厂板级来源是本机 AndroidR 树提交 `23172a1571bd91156032cc9fef16284a82b63d2c` 的 `arch/arm64/boot/dts/19781/sm8150-camera-sensor-mtp.dtsi`。现匹配内核 source354 为 `5b0e7a9ac5b311a4c4fe17cf48b7ed4fc9a7b91d`，其中仅主摄有 LC898219XI／`lens-focus`。两路 BU64253 分别在不同 CCI bus 上，地址相同不会互相碰撞；不改主摄 lens 或把其初始化套给另两路。

原件来自115的本机 vendor 缓存；Sunny IMX319 SHA `e2d68359…21704`，另名为 Qtech 的 IMX319 文件 SHA `e3f572ec…4b5c`，其内部 moduleName 实际也为 Sunny，不能凭文件名认证供应商。两个文件的 actuator 协议和本轮相关参数相同。长焦优先使用326后来保存的本机原厂版本 SHA `823404fc…c77`；与115旧版本的 actuator 语义逐项一致，不能把整份 BIN 哈希不同误判成镜头协议变化。

两模组各以274已匹配的 XSD／受限 ParameterParser 独立解出 actuator XML，与有界直接 decoder 核对地址、位宽、三条初始化、位置命令及初始码。只在分析副本关闭其它 root 标记，所有数据区字节保持；原件、完整 XML、供电与 AF tuning 留在 `E:/edk2-samurai-out/kernel450/lens-scope`。没有读取新的 EEPROM／NV。

位置表中的 `registerAddr=0xff` 是特殊语义。281保留的本机原厂 `camera.qcom.so`（SHA `e2b1b9b6…a70dde`）在 `CamX::Actuator::MoveFocus` 的 `0x41e0a0/0x41e0d0` 生成高字节，并在 `0x41e17c…0x41e18c` 对 0xff 分支选择命令：

```c
command[0] = 0xc4 | ((dac >> 8) & 3);
command[1] = dac & 0xff;
```

这不是向地址0xff写一个字节，也不是主摄的0x84＋16-bit协议。广角初始化为 `d0=71`、`c8=01`、`f0=80`；长焦为 `d0=78`、`c8=01`、`f0=80`，相应等待5／100／10µs。VAF 后原厂等待10ms、关闭后1ms；目前没有独立 BU64253 数据手册最短上电／掉电间隔证据，不能照搬 LC898219XI 的100ms规则。未确认可读 chip-ID／位置反馈、park 或待机命令，草稿没有添加这些操作。

两模组各自原厂 nominal tuning 的初始码、区域与换算后的默认搜索范围已保存私有候选，并以原件指纹关联；这是原厂默认搜索起点，**不是已核本机个体 AF 端点或屈光度／距离标定**。驱动协议范围0…1023也不等于允许实机扫满量程。后续先在私有调校中按实际模块约束一次标准 AF，检查 Scanning、镜头写入、有效 FoM 与终态；不手动遍历0…1023。

当前IPA还要求私有 `autofocus.lens` 与驱动实际model一致才能启用AF；因此底层接入后要单独补匹配BU64253的两份数据配置。没有添加driver／DT就视为已具备AF，也没有把主摄的搜索稳定时间套给这两颗执行器。

## 第五2MP：完整原厂描述已在缓存，下一步是驱动与共享链路

363范围文档引用115当时的六份 BIN 清单；其“没有对应模组配置”只描述115库存。**282已经补取 `com.qti.sensormodule.shine_ov02a1b.bin`，37480字节，SHA `63e2122a9b0003ed8af6eade006e3a5ef7c40beb530fa0d5a6069836e9b3b5fa`。**因此当前不必再从手机提取该文件。

有界解析现已恢复：Shine／slot4，8-bit地址 `0x7a`→7-bit `0x3d`，寄存器地址／数据各8bit，原厂探测地址0x02、期望0x25；单模式1600×1200、CSI DT0x2b／RAW10、单lane D-PHY、声明30fps，**CFA枚举为 `BAYER_Y`（单色）**。88条有序初始化、单条模式写入以及 stream-on/off、group-hold 四组原始命令已完整保存私有 JSON；保留重复写、页切换和延时。未执行OEM库、未用这些表访问硬件。

19781 slot4 是 CCI1/master0、VIO1.8V、P侧L5模拟2.8V、MCLK2／19.2MHz、reset12、GPIO29低态选择；当前前摄占用 MCLK2／reset12／PHY2，GPIO29活动态为高。因此独立sensor节点之外还缺**标准媒体mux／共享资源生命周期**，不能同时给两个 sensor 申请同一 reset／clock／PHY，或让前摄的sleep pinctrl在另一模组取流时切回GPIO29。

现 source354 有 `ov02a10.c`，没有 `ov02a1b.c`。OV02A10缓存来源要求24MHz、ID0x2509，并使用 Bayer 输出；本机描述只按8bit读取0x02的0x25且输出单色。不能仅因前缀相似直接改compatible冒充匹配。CAMSS多个层已有 `MEDIA_BUS_FMT_Y10_1X10`，可先复用标准单色 RAW 路径；这不证明当前 IPE／自动调校已支持该模组，也不应套彩色 AWB／CCM。

最小接续是按缓存表准备独立 `ov02a1b` sensor 和单色RAW控制，先协调GPIO29／MCLK2／reset12／PHY2独占，再验证已知0x3d上0x02与相邻识别字节、真实RAW和标准控制。保留0x02只比高字节的原厂语义及完整器件身份未知；不能宣布检测成功。元数据中的934 line length、1738 frame length、300MHz output pixel clock与30fps不能直接相除当真实行时序，仍须从页寄存器／原厂曝光回调恢复正确单位。

本轮最接近实际增量的是453两路 BU64253 草稿，先长焦单路更容易隔离：它不触碰前摄／第五模组共享PHY，也不改变当前主摄链路。所有新硬件操作仍由主线在手机窗口交回后串行安排。
