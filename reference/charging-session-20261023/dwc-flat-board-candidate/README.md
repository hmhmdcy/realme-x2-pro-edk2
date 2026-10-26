# SM8150 combined DWC：native9271 的最小 flat DT 候选

唯一私有 DT 构建已通过，候选仍未部署。产物为 `E:/edk2-samurai-out/charging-management-20261023/dwc-flat-board-private-01/samurai-dwc-flat-private.dtb`，115816B，SHA256 `3c66a954d94ee4e9f59aac8190272dac0f247e592aac254772b043bd9cded9ae`。base 精确为 EUD-off native9271；没有混入未来 IRQ13d3、保护/采证模块、Image503 或其它载体。

[build-flat.py](build-flat.py) 复用已冻结 `inspect-dtb.py` 的只读 decoder，以及系统 `/usr/bin/dtc` 1.7.2。原 DTB、decoder、dtc、固定 combined binding 的输入 hash 都在 [dt-result.json](dt-result.json)。只有三个实际子进程：原 DTB decompile PID732、候选 DTS compile PID733、候选 DTB decompile PID738，全部真实 wait rc0；原件和执行源码保留。没有 make、kernel object/Image、boot封装、284 storage helper、共享源码/config写入、SDK、Git或设备操作。

## 实际变更与全树约束

旧 `/soc@0/usb@a6f8800` wrapper 及其 `usb@a600000` child 合为唯一 `/soc@0/usb@a600000`。compatible 是 `qcom,sm8150-dwc3`, `qcom,snps-dwc3`，reg 是本机原厂 aperture 与 fixed binding 结构例支持的 `0xa600000/0x100000`。旧 wrapper 的四个 bus-only 属性被移除。迁移的 readable DTS 差异在 [native-flat-only.patch](native-flat-only.patch)。

- 原六 clocks/名字、assigned rates、GCC reset `0x1a`、GDSC `0x04`、两条原 interconnect raw specifier 保持。
- core GIC SPI133/HIGH 合入最前，其后原 wrapper 的 SPI130/HIGH、SPI131/HIGH、PDC9/BOTH、PDC8/BOTH、PDC6/HIGH 保持；六名字顺序为 `dwc_usb3,pwr_event,hs_phy_irq,dp_hs_phy_irq,dm_hs_phy_irq,ss_phy_irq`。
- 原 child 的 stream `0x140`、两个 PHY引用、`peripheral`、五个本机quirk、`usb-psy-name="samurai-usb-input"` 全部搬移。
- ports子树只换路径，所有属性 raw保持。DWC endpoint `0xc2` 与 QMP endpoint `0xcc` 双向引用保持；没有新增 controller phandle 或第二个控制同硬件的设备。

decoder 比较完整 expected tree：965→964节点、3965→3958属性；**958个非USB节点** 的全部属性原始bytes逐字相同，5个ports后代的全部属性原始bytes逐字相同。即 EUD/Type-C disabled、GPIO、PMIC、相机、PHY/供电节点和其余所有外部引用保持。reserve table、boot CPU和FDT版本也保持；新controller原始属性、IRQ provider解析及搬移路径均在结果中，可独立复核。

## 诊断与 schema 范围

原/候选 decompile 各27条既有非USB warning。执行器的首个诊断比较仅归一输入DTB路径，遗漏 dtc `-o` 输出DTS文件label，故原结果如实保留 `normalized_decompile_diagnostics_equal=false`。[diagnostics-addendum.json](diagnostics-addendum.json) 绑定同一批原stderr，**只去掉 `: Warning ` 前的文件label** 后全部warning正文及顺序完全相等，没有去掉任何warning或重跑dtc。

固定 `qcom,snps-dwc3.yaml` 明列SM8150，六钟/六IRQ/flat DWC common形状有源码依据。环境没有 `dt-validate` 或 Python dtschema；未做完整schema验证。固定 new/common binding 均未直接声明本机既有 `usb-psy-name`，它是必须保留的本地native-budget扩展，不能为了schema静默删掉。不能把本次 dtc/raw比较称为上游schema通过、probe成功或实体恢复通过。

## 采用前剩余配套

本候选目标是 **实际 #502 成功采用之后，另建一个独立的新事务**，配套 OEM 的非IRQ USB模块 `c70a2ef09c48af4c51c60bf4081c63229464587ac3f5ad47f9c121209d1d2c17`。它不属于本次已经 prepared 的 #502 动作，也不是未来 IRQ/保护/采证 cohort；不得把这份DT插入那些冻结事务或复用其身份。

当前 #502 已有 combined driver 的链接证据来自 root 的 [unified-driver-image502-evidence.json](../../charging-management-20261023/unified-driver-image502-evidence.json)，无需仅为这份DT重编Image。但现 R8 USBinput native-retain 硬编码旧路径，必须与 OEM 独立 `usb-input-flat-consumer-candidate` 一起核对并在新启动采用；此叶没有安装/替换模块。旧boot/adoption/driver-parent身份不能认证新拓扑。`a600000.usb` 的预期名称、新PM依赖、native预算、NCM及充电保护仍需受控新启动与硬件窗口验证。

本次不改描述符/startup500、PMIC源策略、充电请求/保护、桌面或UPower。combined owner仍无完整 DEVICE failure abort；BCR控制权、IRQ/work/端点排他与 HALT未知的DMA安全收尾是另外的实现/证明边界。此DT不宣称这些已闭合。
