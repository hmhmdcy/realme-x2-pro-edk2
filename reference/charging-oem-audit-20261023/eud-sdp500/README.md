# EUD hub与SDP500：原厂/规范离线审查

本代理未访问手机、EUD API、SDK运行环境或任何USB句柄，未改shared/main/Image/descriptor/硬件。仅读取PC缓存与原厂源码；定向网页只查原始USB规范和官方文档。没有重复CTL API位表或编造新硬件patch。

## 当前能行动到哪一步

**先把SDP500问题收敛到真实EUD端口7的配置/功率拒绝证据；暂没有资料支持可以直接采用的SM8150运行期EUD旁路事务。** 当前CDP没有被native100错误压低，不能当作已存bug修。不要重复在相同描述符条件下盲试500，也不能用self-powered伪装、猜strap或写主机功率规则绕过授权。

## 实际缓存的关键新字段

根会话已用只读GET确认100mA配置下0525 NCM在05c6:9500 EUD hub的**端口7/config1**，端口1是9501 control；本子任务没有重做设备查询。原始完整NodeBase64在私有 `E:/edk2-samurai-out/charging-management-20261023/usb500-baseline-r6-host-01/metadata-private.json`，其SHA256为 `3c4f3cb65a00b769ab07fab99327636da4be722f231705542a113c8445c7d505`。

独立只读重解该76B原件，见decode-cached-node.py/cached-node-result.json：

| 字段 | 实际值 |
| --- | --- |
| NodeType/HubDescriptor | 0；length9、type0x29、7ports |
| wHubCharacteristics | 0x0000 |
| bPwrOn2PwrGood/bHubContrCurrent | 1（2ms单位）/0mA |
| DeviceRemovable bitmap | **0x00，端口7向主机声明removable** |
| PortPwrCtrlMask | 0xff |
| HubIsBusPowered | true |

USB2表11-13的DeviceRemovable bit1对应port1，bit7对应port7，0是removable、1是non-removable。故“物理在手机内部”不等于“当前向USB主机声明为compound non-removable”。[USB2.0原规范，正文418页/PDF446页](https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/2656.usb_5F00_20.pdf#page=446)

HubIsBusPowered是Windows报告的bus/self供电状态：[Microsoft字段定义](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usbioctl/ns-usbioctl-_usb_hub_information)。它和hub descriptor里的wHubCharacteristics不是同一字段；后者的电源切换/过流位不是self-powered位。0mA的bHubContrCurrent也不是证明hub物理不耗电。

旧54版对无设备端口的全零35B响应提前拒绝；根已用62版对保留182个原response重解。本审计不把旧“只看到port1/没有NCM”摘要当当前基线，也没有删改旧原件。

## 三种权限要分开

USB2.0 §7.2.1/7.2.1.1（正文171–172页/PDF199–200页）把bus-powered hub总预算与**external ports**的每口1 unit load分开，并容许hub及non-removable functions共用分配。不能仅凭“bus-powered”就否定所有compound内部功耗模型；但当前DeviceRemovable=0，使端口7按普通removable口处理的100mA约束更有依据。总线供电外接口不会因其他口空闲自动获得500mA。[原规范](https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/2656.usb_5F00_20.pdf#page=199)

BC1.2 §1.2与表5-2区分普通SDP配置额度和完成充电口识别后的充电权限；真实CDP可给PD最高1.5A充电，不以USB configuration或普通suspend规则为前提。这不把EUD的下游口描述符改成CDP，也不使主机一定接受NCM的500配置。[USB-IF BC1.2原文，正文1/44页](https://e2echina.ti.com/cfs-file/__key/telligent-evolution-components-attachments/00-24-01-00-00-14-32-53/USB_2D00_IF_5F003575606C45513575C4893C682800_Battery_5F00_Charging_5F00_Specification_2D00_1.2_2900_.pdf#page=12)

实际source354的composite.c1037–1059向gadget传递配置功耗；suspend2606传2mA，resume2632–2649恢复配置或默认100。DWC gadget.c3156–3178把这一软件vbus_draw值转到PHY/usb_psy。它是USB设备框架的额度变化，不是ADC电流，也不是BC1.2物理检测结果。

当前 `samurai-usb-input-decode.h` 65–66把新鲜有效CDP识别为1500000；88–101的apply_udc只处理SDP，**不会把CDP与raw DWC100取min**。原test-protocol58明确验证CDP+UDC2000仍1500000。父会话确认r6仅换charger，source仍c777…；诊断里的native_ua是source有效budget字段，不能把它误标为原始DWC回调。没有发现CDP误压100的实现缺陷。

原厂19781 DTS pm8150b.dtsi244/246分别给USB500和CDP1500；`oplus_charger.c`3555–3565按charger_type区分二者。这支持分类语义，不能把原厂普通USB500常量直接当本机当前EUD拓扑已获主机许可。原厂来源固定为Realme AndroidR提交23172a1571bd91156032cc9fef16284a82b63d2c，缓存路径/hash见上级audit.json。

## 正常EUD关闭、数据旁路与描述符来源

本机原厂库 `E:/eud-host/quic-eud` HEAD693741a3b0448690402539ed0e6af067510e386f、origin [quic/eud](https://github.com/quic/eud/tree/693741a3b0448690402539ed0e6af067510e386f)，工作区无改动。定向检索inc/src未找到hub bmAttributes/bMaxPower、self-power、ROM/OTP/strap来源或可直接调用的数据bypass流程。HOST_EUD_DIS只出现在定义/状态说明，不足以推出可执行切换顺序。未执行任何该库API。

有真实的原厂**关闭EUD**实现，但证据范围止于此：

- 已缓存下游 `drivers/soc/qcom/eud.c` 159–175把CSR_EUD_EN清0，并在secure_eud_en存在时通过SCM清EUD_EN2；178–208提供enable参数。98–156的enable反向还依赖usb power_supply、类型以及extcon事件。[对应缓存来源](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/soc/qcom/eud.c)；该仓库URL由本机bare-cache的origin核实。此旧下游提交与上述AndroidR充电来源有意分开，不混称同一树。
- 实际source354 `drivers/usb/misc/qcom_eud.c`45–69有SCM mode-manager + CSR开关，enable还调用usb_role_switch。当前samurai DTS371–381明确没有给这一全EUD驱动提供可用的role-switch/secure SCM绑定，而使用自定义qcom,sm8150-eud-com；该COM驱动probe会自行保持/打开EUD。
- 这些函数都没有确认正常OS中的DWC3直连重枚举、路由复位、与当前COM console/RX工作协同、500授权成功或PHY供电描述符变化。旧367流程面向bootloader，包含console退休/解绑与EUD关闭，不能证明常态数据bypass。

未找到原厂材料说明05c6:9500的descriptor由哪块ROM、OTP、strap或固件表生成。DWC3/configfs的NCM descriptor属于另一个child（0525），改它不会改变父EUD hub的bus-power/removable声明。板上regulator供电连接也不能单独证明USB对外供电描述符应为self-powered。**没有依据提交供电描述符或硬件位补丁。**

## 最小后续路径

1. 复用已建立的真实NCM port7映射。若另有获批500实验，保留**失败当时**port7 ConnectionStatus、ConfigurationValue、PnP problem/事件及合法SET_CONFIGURATION/native事件；专门区别功率不足拒绝、枚举失败、端口无设备和UDC没恢复。此处不安排/执行实验。只在错误字段确实支持功率拒绝后再提高根因置信度。
2. 在现有只读窗口补EUD hub本身的configuration descriptor（bmAttributes/bMaxPower）和实际GetStatus设备self-power状态，并保存原字节；这些补功耗记账依据，不是让主机改变预算。当前Node不能提供这些完整字段，也不能反推描述符生成硬件。
3. 若500被当前removable/bus-powered拓扑拒绝，继续用已接受100；改变电脑外置hub或换供电更强的SDP口并不自动消除手机内部EUD口的声明。真实新鲜CDP识别则走当前已有1500权限，保留100的数据描述符不妨碍该独立充电权限，但仍需尊重整机输入/保护上限。
4. 真要研究正常无EUD数据模式，先补Qualcomm SM8150平台文档/原厂完整正常模式序列及EUD硬件descriptor来源，再设计有恢复通道的独立OS切换验证。现有关闭函数可作代码依据，不能当本机已可安全执行的bypass事务。

公开材料使用的是USB2.0与BC1.2原始规范文本，非第三方博客；USB-IF[USB2官方目录](https://www.usb.org/documents?search=usb+2.0+specification)和[BC1.2官方目录](https://www.usb.org/documents?category=&search=Battery+Charging)可核对版本。官方ZIP的本次直接下载403，未尝试绕过；网页工具从TI公开附件读到了原规范。未声称已审完官方目录的全部后续ECN，也未因此改变设备。cache-spec-pdfs.py/fetch-primary.py仅保留下载尝试代码，未产出成功下载的PDF，不是设备工具。
