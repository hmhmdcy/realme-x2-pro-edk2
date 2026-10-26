# 466：长焦 mode2 的 CSI/link 候选已收敛

同一S5K3M5SX原厂公开驱动支持：本机19.2MHz、PLL组 `(0x030e=3, 0x0310=113, 0x0312=0)` 的 **mode2候选link_freq为723200000Hz，D-PHY每lane数据率1446400000bit/s**。这是以匹配SX模式表及MIPI元数据约束的推导，尚无本机物理时钟测量，也未取得0x0312的数据手册位定义。本轮不修改驱动、DT、SDK、正式mode3或465冻结件。

## 同传感器的表与数据率依据

[OnePlusOSS固定源码](https://github.com/OnePlusOSS/android_kernel_oneplus_mt6893/blob/48f1797695e24d46986a7c87dd91dd21cbf8c342/drivers/misc/mediatek/imgsensor/src/common/v1_1/s5k3m5sx_mipi_raw/s5k3m5sxmipiraw_Sensor.c)明确为S5K3M5SX，初始化ID0x30d5、24MHz、4-lane、RAW10。逐案核对scenario函数→setting函数→完整模式表，并与各自mipi_pixel_rate及功能查询返回路径对应，10条链全部相等。其OP选择组0x0308/0x030a/0x030c均为8/1/0，与本机mode2/3一致；没有用另种Samsung CIS同地址代入。

| OnePlus模式 | 0x030e / 0x0310 / 0x0312 | 声明MIPI像素率 | 换算lane bit/s | 对应link Hz |
| --- | --- | ---: | ---: | ---: |
| pre，及同表用途 | 3 / 99 / 1 | 316800000 | 792000000 | 396000000 |
| cap | 3 / 90 / 0 | 576000000 | 1440000000 | 720000000 |
| custom1 | 3 / 74 / 0 | 473600000 | 1184000000 | 592000000 |
| custom2，二合一60fps | 3 / 90 / 0 | 576000000 | 1440000000 | 720000000 |

上述所有模式的控制pclk均为482MHz，而MIPI数据率分三种；控制pclk不能替代传输时钟。custom2二合一仍用0x0312=0，也排除了仅按binning猜分频的做法。

Samsung署名的[固定SX SetA](https://github.com/LineageOS/android_kernel_samsung_exynos9820/blob/a412cfaf86b980ce35cae96a35f678c8ea551575/drivers/media/platform/exynos/fimc-is2/sensor/module_framework/cis/fimc-is-cis-3m5-setA.h)另有10组显式mipi_datarate。其[头文件](https://github.com/LineageOS/android_kernel_samsung_exynos9820/blob/a412cfaf86b980ce35cae96a35f678c8ea551575/drivers/media/platform/exynos/fimc-is2/sensor/module_framework/cis/fimc-is-cis-3m5.h)固定26MHz，mode表030e=4、0310=104、0312=0，对应声明每lane1352Mbit/s，即link676MHz。该表省略0308/030a，本轮没有猜补它们的默认值；它只作为显式bitrate的独立旁证。同仓SetB明确是3M5SM、PLL寄存器映射不同，其调试字段名不用于SX结论。

## 仅对已覆盖0／1编码成立的推导

匹配上述SX选择组时，20条表／元数据关系支持：

`link = MCLK × reg[0x0310] ÷ reg[0x030e] ÷ (reg[0x0312] == 0 ? 1 : 2)`

RAW10、4lane的传输像素率为 `link × 2 × 4 ÷ 10`，lane bit rate为 `link × 2`。公式来自同CIS原表与传输元数据对应；没有从481930000的VT/outputPixelClock倒推，也不外推0x0312其它取值或声称得到了其正式位定义。[分析器](inspect-link.py)、[20条实际对应与固定来源哈希](link-validation.json)。

| 本机原厂模式 | 0312 | link候选Hz | lane bit/s候选 | 传输像素率候选 |
| --- | ---: | ---: | ---: | ---: |
| mode2，4208×2368，HFR标签保留 | 0 | **723200000** | **1446400000** | 578560000 |
| 现有mode3，2104×1560，NORMAL | 1 | 361600000 | 723200000 | 289280000 |

mode2现在有可供下一增量使用的Linux link_freq候选。mode3现有723.2MHz元数据可能过报两倍，保留为独立待验证问题，不改变已通过的mode3消费者事实或同SOF/LTM历史，也不在本轮顺手修改正式栈。

下一增量可据465私有53写入与IQ几何草稿追加mode2，仅编译受影响sensor目标；检查每模式link选择／endpoint允许值与实际读回，再验证该模式CSI、控制时序和同SOF FULL/PD10。沿用原厂完整PLL表，不能为凑候选频率改写0x0312或倍频字段。mode2正式接入及本机物理频率仍未验收。

8份检索到的源文件按固定提交私存kernel466；其中新SetA/SetC与Nothing文件只作补充盘点，不计入上述20条证明。公开收据固定来源哈希，本页明确这些用途与限制，原厂／本机私有表不公开。465全部冻结输入及私有分析哈希前后保持。没有新增HAL逆向、手机访问、SDK绑定、源码/ext4构建目录访问或编译。
