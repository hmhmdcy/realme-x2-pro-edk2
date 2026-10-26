# 本机 USB 父复位与统一主线驱动：只读调查

本机有真实 USB controller block reset，拥有者是当前 `dwc3-qcom-legacy` 父设备；child 的 optional reset 为空不能推导整个 USB block 没有 reset。现有固定源码同时已有较短的统一 `qcom,snps-dwc3` 驱动，可作为后续迁移基础。本轮没有修改 DT/源码/config、构建、跑旧测试、设备/SSH/PM/SDK/Git 操作，也没有生成可部署候选。输入/字段摘要见 [findings.json](findings.json)。

## 实际控制权及证据限制

native DTB `9271d9cc…14358` 的 `/soc@0/usb@a6f8800` 包含 GCC phandle `0x2e`、reset ID `0x1a`。固定 #503 `qcom,gcc-sm8150.h:239` 将 ID26 命名为 `GCC_USB30_PRIM_BCR`；`gcc-sm8150.c:3717` 将其映射到 GCC offset `0xf000`、默认 bit0。child `/soc@0/usb@a6f8800/usb@a600000` 没有 resets。PHY 各自的 0x0f、0x12/0x11 属于 HS/QMP provider，不是 DWC DMA 停机接口。

[legacy 父源码](../dwc-resume-error-independent-review/source--drivers--usb--dwc3--dwc3-qcom-legacy.c) probe:749 独占取得 optional reset array，755 assert、等待10..1000us、763 deassert，然后开钟并 populate child。remove:842 先 depopulate child、释放 clocks/interconnect，最后 assert。它的 runtime/system suspend/resume:426/462 只管理父 clocks/interconnect，未提供失败时 reset 方法。child/core 不能再私取同一个 exclusive handle，也不能从自身 PM callback 递归调用父 PM 或 remove。

固定 #503 `drivers/clk/qcom/reset.c` SHA `434e63a1…326e8` 的 `qcom_reset_set_assert:25` 忽略 `regmap_update_bits` 与读回的 errno，也不检查读回值；read 仅用于 write-completion flush。ops 没有 `.status`，现父又持 array。因此 `reset_control_assert()==0` 本身既非 BCR 位值收据，更非 outstanding AXI/DMA 已完成的收据。主线对应 write-completion 修订也只说明 flush 目的：[2f8cf2c3](https://git.zx2c4.com/linux-rng/commit/?id=2f8cf2c3f3e3f7ef61bd19abb4b0bb797ad50aaf)。通用 [reset API](https://www.kernel.org/doc/html/latest/driver-api/reset.html) 规定 exclusive 控制和 shared 计数，未赋予 USB DMA-drain 语义。

本机19781原厂 [USB DTS](../../charging-oem-audit-20261023/apsd-lifecycle/oem/arch--arm64--boot--dts--19781--sm8150-usb.dtsi):19/50 也把同一 BCR 交给 USB owner；`dwc3-msm.c` SHA `f9977ba4…ee713f` 的 `link_clk_reset:1810` 在关 power-event IRQ 与 UTMI/sleep/core/iface clocks 后 assert，deassert 后200ns再按 iface→core→sleep→UTMI 开钟；`block_reset:2109` 有1..1.2ms asserted 与10..12ms恢复等待。其错误处理:1878 使用独立 restart work、in_restart、断开/状态机与 power-collapse；不是 child PM 中一个裸 reset 调用。本轮检查的这些源码、binding 和官方 API 未提供可直接移植的“BCR asserted 后所有旧 USB AXI 写已完成”契约。不能把原厂执行过 block reset 推成当前软件可立即清 event 地址/释放 DMA/退 PHY 的证明。

## 统一驱动是否已经可用

[new glue](../dwc-resume-error-independent-review/source--drivers--usb--dwc3--dwc3-qcom.c) SHA `facf03c8…b9c4d`。它的 `struct dwc3_qcom:71` 内嵌 `struct dwc3`；probe:703 给 core 同一个 `dev`，设置 `ignore_clocks_and_resets=true`，由同一 owner 持 exclusive BCR、clocks、QSCRATCH。PM:748..825 在一个 callback 中按 core suspend→glue suspend、glue resume→core resume 排序。相对 legacy 父/child 两个 PM 设备，这能减少复位方法需要跨两个 owner 的问题。

#503 Makefile:55/56 已由同一 `CONFIG_USB_DWC3_QCOM=y` 编入 new 和 legacy 两个对象，无须新增 config。new 只匹配 `qcom,snps-dwc3`，legacy 只匹配 `qcom,dwc3`。固定新 binding `qcom,snps-dwc3.yaml` SHA `d6f619e1…b727b` 明确枚举 SM8150、要求六钟与5..6个中断；旧 binding 标 deprecated 并指向 combined binding。当前 #503 的 sm8150*.dts/dtsi 仍全是旧 nested 结构，没有找到本树内已经迁移且有 binding-validation 收据的 SM8150 flat 板例。可复用 binding 中 SDM845 的合并结构，不能照搬其 stream ID、IRQ 或供电；本机原厂已给出同基址1MiB aperture。

new driver 仍只在 probe pulsing reset，没有 resume-failure reset/abort 方法。它仍调用当前 core 的 ignored-gadget-error 路径；若以后 core 负返，glue resume 后的负返也没有自动回收已开启 glue clocks。统一 ownership 是基础，不是 HALT 未知/PM unwind 已修复。

## native9271 的精确迁移边界

目标逻辑节点为 `/soc@0/usb@a600000`；移除原 wrapper/child 双设备，不并存两个控制同一硬件的 provider。以下是字段计划，未生成 DTB：

| 字段 | 必须采取的本机迁移 |
| --- | --- |
| compatible/status | `qcom,sm8150-dwc3`, `qcom,snps-dwc3`，保持 enabled；旧 `qcom,dwc3`/`snps,dwc3` 子设备不保留为第二设备。 |
| reg | 不能复用 wrapper 的 `a6f8800/0x400`，也不能只用 child 的 `a600000/0xcd00`。合并以 `0x0a600000` 为 base，范围须包含 new driver 的 `base+0xf8800/0x400` QSCRATCH。本机原厂 DTS 和 new binding 结构例都给1MiB，可据此采用 `reg=<0 0x0a600000 0 0x100000>` 再验证资源边界。 |
| clocks | 原六组原样：GCC IDs `0x0c,0xac,0x05,0xb0,0xae,0xbb`，names `cfg_noc,core,iface,sleep,mock_utmi,xo`；assigned IDs `0xae,0xac`、19.2/200MHz 保持。原厂特别指出本机两 USB 共用 SEC CLKREF，不能改成 PRIM CLKREF。 |
| resets/power-domains | 原 parent 的 GCC `0x1a` 与 GDSC `0x04` 移到合并节点；不加 PHY reset、不新增子节点 duplicate owner。 |
| interrupts | 合并为一个 `interrupts-extended`：先 `intc/GIC_SPI133/LEVEL_HIGH`，再原 parent 的 `intc/SPI130/HIGH`、`intc/SPI131/HIGH`、`pdc9/EDGE_BOTH`、`pdc8/EDGE_BOTH`、`pdc6/LEVEL_HIGH`。names依次 `dwc_usb3,pwr_event,hs_phy_irq,dp_hs_phy_irq,dm_hs_phy_irq,ss_phy_irq`。不能直接复制旧 parent 的五组而漏 core IRQ，也不能混用原厂旧IRQ数字。 |
| IOMMU/interconnect | child 的 `apps_smmu` phandle `0x2d`, stream `0x140`, flags0 移到合并节点；parent 两条原 raw interconnect specifier/names 原样保持。 |
| PHY/dr_mode | child 的 `<0xca>,<0xcb 0>`、`usb2-phy,usb3-phy` 及 `peripheral` 移到合并节点。HS/QMP provider 节点地址、供电、reset、phandle 全不动。 |
| quirks | child 的五个空属性全部搬移：`snps,dis_u2_susphy_quirk`, `snps,dis_u3_susphy_quirk`, `snps,dis_enblslpm_quirk`, `snps,dis-u1-entry-quirk`, `snps,dis-u2-entry-quirk`。不因公共例只含两项而丢失本机差异。 |
| graph | 搬移原 ports 子树并保持 endpoint phandle/remote-endpoint；当前 controller 两层本身无 phandle，native没有 USB alias 或字符串路径引用要改，但外部 QMP endpoint仍依赖原 graph。 |
| bus-only字段 | 旧 wrapper 的 `#address-cells/#size-cells/ranges/dma-ranges` 是旧 child bus 结构，不能当成新的 nested 结构保留；依据 flat binding处理，ports 自己的 cells 保持。不臆加 dma-coherent、role/PD、extcon。 |
| GPIO/电源 | 当前两层USB节点和两PHY节点都没有 gpio/pinctrl 属性；不能添加原厂 GPIO/PMIC controls。HS supplies原解析为 regulators-0 `ldo5/ldo2/ldo12`，QMP supplies为 regulators-0 `ldo5` 和 regulators-1 `ldo3`，所有原 phandle值保持；EUD/Type-C disabled也不动。 |
| native预算 | `usb-psy-name="samurai-usb-input"` 从 child搬到合并节点，保证同一dev的 core 继续读取该 supply。不得变 USB descriptor、PMIC APSD/PD/QC 或充电限值。 |

`phy_get()` 实际为调用 dev→PHY 创建 `DL_FLAG_STATELESS` link并持 provider引用，迁移后 consumer dev 从旧 child换为合并dev；PHY本身和 regulators引用保持。它不是 devres/MMIO 防释放许可。新 core 还会从合并节点取得 IOMMU/PM domain，不能只留旧 parent 资源再期待 child 自动继承全部属性。

用已冻结 parser 只读解码原9271的全部965节点/3965属性：旧 parent和child均无 `phandle` 或 `linux,phandle`，所以没有待重定向的这两节点的 phandle ID。整个旧子树唯一 phandle是DWC port1 endpoint `0xc2`，外部 QMP `/soc@0/phy@88e8000/ports/port@1/endpoint` 的 `remote-endpoint` 指回它，必须保留；反向DWC指向QMP `0xcc` 也保持。全树没有含旧wrapper路径的字符串属性，也没有 USB alias。扫描范围是这份固定DTB，不代替未来新DTB的全部引用校验；软件源码中的硬路径另列如下。

## 必需软件配套与最小顺序

当前 R8 [samurai-usb-input.c](../../charging-management-20261023/samurai-usb-input.c) `b712764f…7098`:236 的 native-retain 硬编码旧路径 `/soc@0/usb@a6f8800/usb@a600000`。迁移后会漏掉模块自持引用，而 new core仍持 power_supply；必须先提供最小旧/新实际 controller 匹配支持，维持 `native_retained`/unbind保护，再与 DT同次启动采用。冻结的未来IRQ源也继承该依赖，不能当作已支持 flat。不要热卸当前 native provider。

UDC `usb_add_gadget` 以 controller device名创建UDC；新节点同为 `usb@a600000`，预计仍为 `a600000.usb`，但新驱动为 `dwc3-qcom`、sysfs父链/设备数量变化必须新启动实证。rootfs startup500、configfs、capture/postboot多数固定该UDC名，需保留并验；`inspect-managed-boot.py` 等直接读旧DT路径、profile中driver/PM父路径必须迁移。当前服务的native_retained门和新manifest/loaded-note也必须绑定真实新模块。不能借旧boot/adoption材料认证新拓扑。

单独BCR调用路径没有PMIC/VBUS开关写，也不会自动生成新native授权；实际物理源仍须新鲜采样。当前 core `vbus_draw_work`→provider `set_property` 只更新内存 native allowance；标准 composite disconnect请求0、reset请求100mA。SDP采用该native数值，CDP仍受独立源预算及900mA板级cap。reset owner必须先解决真实disconnect/current回调工作与保护采样的序列，不能以BCR值保留旧500许可，也不能直接写PMIC或预算冒充主机授权。

最小下一步是先决定当前实际 adopted cohort，独立生成上述 **flat DT+USBinput路径兼容** 候选，静态核完整 raw diff/graph/IRQs/supplies与binding，再只构建受影响USB模块并保留精确回退；不必为“驱动已存在”重编整Image。基线硬件窗口先验证同源充电保护、native额度、NCM和普通PM事实，之后才考虑同owner reset方法。HALT未知的失败终态仍缺 producer/lifetime串行、实际BCR生效/停止DMA证据和PM一致收尾；不能目前就把这些缺项填成返回0或负返退电。旧r5 EUD console/50秒证据不代表当前EUD-off新boot，不能用它为当前未发生的502失败归因。
