# 阶段124：原厂C-PHY表、共享电源与频率契约

2026-10-12。阶段124完成本机camera_8150三相PHY表129项移植（保留与参考不同的三处0x24）、C-PHY输入/能力守卫、频率比例修正及本机共享L3 1.2V供电模型。#124完整Image/770模块/DTB和模块包通过，实际C/ASan/UBSan与schema正反例通过；CAMSS保持disabled，未部署，settle实际时序、CPAS/QoS、IOVA下界和sensor仍开放。完整rootfs仍122匹配121；手机仍118/DPU2/GPU1和11来源校验，完整goal active。

## 原厂活动源码优先于外国板补丁

互联网重验[固定Hotdog commit47087509c4289c2580c54f5433e55366b2e00445的0089](https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0089-media-qcom-camss-add-SM8150-C-PHY-support.patch)，remote与已有缓存字节相同；它是外部bring-up参考，并非本机已通过或主线合入证明。

本机AndroidR drivers/media/platform/msm/Makefile的TARGET_PRODUCT:=msmnile选择camera_8150，不能拿同仓库generic camera/ais目录冒充实际使用驱动。检查四目录的同名cam_csiphy_1_1_hwreg.h，活动camera_8150表有三trio×43项共129个ordered tuple，无内部条件编译；其SHA3c0e65eacee345e8bb02906ab7ca7d9da30cad249eea7bbfa908d36db678f539。比0089的index35/78/121三处0x09b0/0x0ab0/0x0bb0应写**0x24**，参考为0x23。generic camera/ais各有12项差异。最初一致性断言失败，进一步沿Makefile找到活动目录，改为明确记录差异并使用全部原厂129项，不把不一致改成“验证相同”。详情[native source报告](../reference/kernel124/native-phy-contract-validation.json)。

7.3驱动按本机v1.1接入native三相表，只为CAMSS_8150设置三个表指针；其他版本用kzalloc保持null，stream在get_lane_mask/频率/MMIO之前拒绝未实现C-PHY。每trio独立指针避免跨子数组做指针运算，按输入trio顺序写表；两byte settle、DNP跳过与ordered重复地址保留，不去重寄存器写入。原厂0x814 odd lane bits、common reset0x800=1/1ms/0、11个IRQ mask也一一建模。活动cam_csiphy_soc.c的v1.1选择明确data_rates_settings_table=NULL，因此数据速率专用表函数对本机版本不写额外寄存器，不照搬其他PHY版本的表。

## C-PHY输入与链路频率

端点允许1..3 trio、每项0..2、不重复、不带clock-lanes/lane-polarities、只允许ABC line-order；未实现排列返回EINVAL，不能接受后静默忽略。D-PHY保留clock与最多四data lane，另拒绝clock/data重复及越界。TPG链接明确is_cphy=false，避免先连sensor C-PHY再连TPG遗留selector；CSID gen2 RX配置设置PHY_TYPE_SEL。

按[Linux官方CSI-2文档](https://docs.kernel.org/driver-api/media/tx-rx.html#pixel-rate)，pixel_rate=link_freq×2×lanes×16/k/bpp，k为D-PHY16/C-PHY7。当前本地v4l2-common.c在没有direct link frequency时采用pixel_rate×mul/div，因此本地C-PHY fallback传**mul=bpp×7、div=lanes×2×16**，D-PHY仍bpp/(2×lanes)。直接LINK_FREQ/mbus频率由V4L2 helper优先，不乘比例。0089没改这一缺口；2026-07-29的[v9 WIP频率提案](https://lists.openwall.net/linux-kernel/2026/07/29/2422)给出不同方向的encoding factor，结合当前helper和公式核实后未盲搬。该[v9 cover](https://lists.openwall.net/linux-kernel/2026/07/29/2407)自己说明WIP，其他设备测试不等于本机验证。

settle_count提升u16，防零timer/无效频率、负数转无符号和超过16bit，除法用64bit避免高频截断。**当前85ns+6UI推导沿参考实现，仅离线候选；原厂实际用HAL settle_time/200000000，HAL参数和本机传感器mode仍未解析，不能证明该C-PHY时序适用于真机。** 此处保留硬件开放项，CAMSS节点仍disabled。

## 本机共享1.2V供电模型

四个19781 CSIPHY都声明mipi-csi-vdd-supply=&pm8150l_l3，csi-vdd-voltage1200000；mainline板继承sm8150-mtp.dts，其qcom,pm8150l-rpmh-regulators/pmic-id c/ldo3即vreg_l3c_1p2，min/max1.2V，已有mdss_dsi0 vdda消费者。改为四CSIPHY各请求vdda-phy，删除从SDM845借来的两CSID vdda-phy/vdda-pll；板级&camss只引用既有L3，未新增假电源。实际DTB解析确认该phandle对应1.2V ldo3，并与现有DSI消费者完全相同。

CSIPHY使用当前7.3已有regulator_bulk_enable/disable与runtime-PM生命周期，电源引用保持每个PHY与DSI独立，不写共享电源GPIO。真实函数fault harness从DSI保有1个引用开始，pm_resume/supply_enable/clock_rate/clock_enable四故障分支均释放自身资源、保留已有引用；正常开关也返回1。**原厂活动camera_8150 C文件未找到这两个custom供电属性消费者**，本轮映射依据DTS意图及mainline消费者合同，不是实测原厂开启电气波形或真实相机采集证明。

## 自动验证与交付

[原生C验证](../reference/kernel124/cphy-c-validation.json)直接抽取候选实际函数，未重写被测函数body：parser18反例/5正例，频率35个官方公式oracle、2 direct频率/6无效情形；原厂129 tuple逐项精确一致，15个ordered非空trio排列逐条MMIO trace、一个完整common/table/IRQ enable trace、7个settle边界和D-PHY mask回归；4个电源故障及正常开关。gcc Wall/Wextra/Werror+ASan/UBSan，遵循kernel已有unused-parameter/sign-compare/missing-field-initializers排除。首次host编译遇到既有kernel初始化/符号比较警告，补齐上述kernel式编译选项；另stub dev_dbg需消费dev参数，修正后保持Werror。没有删除测试或改写actual C使其通过。

[实际stream/TPG守卫](../reference/kernel124/stream-guard-validation.json)另7场景：null regs/null C-PHY表均零lane_mask/频率/MMIO/enable；实现C-PHY分派、旧D-PHY null regs回归；C-PHY链接后TPG清selector、缺sensor拒绝。这里MMIO、时钟和电源均host stub，不算硬件数据流验收。

[实际DTB严格schema](../reference/kernel124/camss-schema-validation.json)保留7反例，dtschema2026.9 CLI对disabled缺required的压制仍用decode_dtb+iter_errors绕过过滤严格检查。[endpoint schema](../reference/kernel124/endpoint-schema-validation.json)新增5正例和6反例：4trio/越界/重复/clock/polarity/非ABC全部拒绝。okay节点只存在私有合成DTB，没有上机。绑定dt-doc/mk无诊断，实际板CAMSS仍disabled、有且仅有native单供电；旧vdda-pll不再是required，也不再允许作为假模型填入。

#124完整Image feb6bfdc7991d26c6278d7d38afba47e86ee04573c78699e9eb3f3ef526fd0c1，59501056字节；DTB 7dd7282d887d3bd87c20fe51633a1aa3b96721e654090f78f7baa1f367a7c5cf，107990字节；CAMSS ko a58e2c52ad133e8722295680edf70191d1abfce45fcc0c2a3c515a03b1a2fb58。完整Image/modules/DTB构建通过，770ko，vmlinux全部Linux-version banner均#124。模块包7067978字节 SHA f12249302c6f76178d576835b4796b878d576df1d40161dbf8871dc81405269a，depmod -e -F System.map零诊断，770条/无symlink/全部依赖存在。与123仅CAMSS ko变动，其余769个stripped ko字节完全相同，fixed IPA bdd85687...保持。patch对123 dry-run通过，source whitespace通过。

隔离源在/home/cy122/pmos-samurai-rootfs122/camera124，E24GiB卷；同进程ensure122访问，schema interpreter先ensure118。首次一处文本替换预期遇到两处匹配即断言停下，已恢复当时写过的5个候选文件自123再准确定位，未改123。port/finalize/package是一次性脚本，完成后不得盲重跑。公开patch包含全部native寄存器，不包含sensor BIN/NV/固件/raw图像或boot-ID。未生成rootfs124，也未把rootfs122包装为124匹配；最新完整软件rootfs仍122匹配121，936包/770模块/21,134条目反向零差异，稀疏SHA4f39f409382d87c5524fbf610fa0d262b3e58629a0f7f1fbee6afc62af5f1933保留。

## 当前手机、长难项与继续次序

同boot只读SSH保持118/taint0/Phosh3492/Phoc3190原PID、DPU累计2/GPU累计1；PCM closed/双amp off muted1 failed0，SLPI offline vdd/vddio0，NV6/source4/vendor1共11个hash保持。没有新phone写入、桌面重启、GPU负载/replay、I2C/GPIO/电源交易。GPU CCU translation fault没有根因修复，不能因taint0和idle认定可用。

活动原厂CPAS选择来自ac40000+0/+4 camera-version/CPAS-version，camera1.7.5配CPAS1.0.0/1.0.1/1.2.0分别175_V100/101/120；ac42000 CAMNOC不能预设101。本轮没在未上电硬件读devmem，没盲写0074 QoS硬地址。下轮先做bounded版本判定和三表比较，使用resource、runtime-PM及失败unwind；IOVA0x07400000下界仍未由31bit mask表达，未解决前不做真实buffer DMA。

PM8008四输入/冷启动地址/0x950 enable、sensor BIN、C-PHY HAL settle属长难项，已留档。本轮推进另一条有证据的数据路径；下轮CPAS有界核对仍卡住则转GPU旧glmark静态buffer/CCU映射或15组其它自动验收，不连续靠offline build冒充功能验收。实际传感器图像、完整摄像头用户态、GPU/显示长稳、定位fix、指纹、充电与休眠仍开放。

新增C/WSL清理已122完成：四obsolete raw充分证明后释放7.26GiB实际占用；当前原WSL VHD不fsck/resize/强制compact。候选都在E，下一复制前检查E122卷free，不能把E宿主free当内卷free。当前122/123/124源和accepted rootfs122都保留，回退118/115不动。完整goal继续active，无人工检查/外发/推送。

收尾：24个Python/2个shell及PowerShell解析通过，841个公开文件检查无私有值，15组硬件保留。E122卷sync/unmount、离线只读e2fsck退出0；E118已因WSL闲置退出处于未挂载，本轮未把它的空挂载目录当文件丢失。宿主C剩余15,225,384,960字节（约14.18GiB），E剩余73,593,237,504字节；宿主free不代表两个ext4卷内部free。原WSL VHD未检查/调整。报告reference/kernel124/host-volume-validation.json。
