# USB input IRQ：离线板级配套候选

根审查最小方案后，已批准并实际完成离线 DTB＋ko。初始 plan-only 原件整组保留在 `history/plan-01/`，含原 plan receipt `df896255…ee4e27`，可按其原相对路径逐项验证。只复用已冻结 IRQ provider（C `0fdafb8b…34b7be5`、FLOAT decoder `a17caa2c…56d548fd`、16例及独审），没有修改驱动算法或重跑旧16例。没有手机、桌面、SDK、Git、共享 source/build 写入，没有 firmware 封装／安装／重启或R9部署cohort。

## 已核实的实际创建链

现已通过的 Image502 私有源码来自精确363 ba61，除BQ之外其它源码与501一致。本叶仅从该已存在私有树读取三份实际文件，`source-read-result.json` 记录 SHA：PMIC driver为 `cba25036…084b9bd`，与 IRQ 作者固定的实际共享源快照逐字相同；OF platform/device 为新的只读引用。没有为读源码重挂卷或调用 SDK。

`drivers/mfd/qcom-spmi-pmic.c` 的 match 表包含 `qcom,pm8150b`。`pmic_spmi_probe()` 先建立 SPMI regmap、获取 revision、保存 driverdata，最后直接 `devm_of_platform_populate(&sdev->dev)`。实际 `drivers/of/platform.c:669–690` 再调用 `of_platform_populate(dev->of_node,NULL,NULL,dev)`；`:457–460` 遍历这个 PMIC 的每个直接 child，`:370` 创建 child；`:161–178` 检查 available／OF_POPULATED、分配设备、设置 platform bus 并 add。提供的 parent 正是 PMIC 的 `struct device`，无须给PMIC追加 simple-mfd 或启用 Type-C。

新 provider 的原 probe 同时验证 Samurai machine、parent compatible／pmic名／SID2、child reg0x1300，随后从这个直接 parent 取 regmap。OF compatible 与模块alias都为 `realme,rmx1931-usb-input`，因此 platform 命名方式不必和 driver.name 相同。新候选 `register_board=1` 检出唯一 enabled compatible 后不再创建软件实例。此处是实际源调用／匹配证据，不是新系统真实 probe 或 IRQ 递送认证；内存不足、父probe失败、domain defer等仍可使运行期不成功。

## DT 变更边界

输入只取当前 boot native DTB `9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358`，115936B；不是 FAT内另一个 A823 DTB。本叶独立解析已核965节点：`/soc@0/spmi@c440000` 为 enabled 4-cell interrupt-controller；直接 parent `/soc@0/spmi@c440000/pmic@2` 为 enabled PM8150B、reg2/0、address-cells1／size-cells0。现无自定义 USB input。`serial@88e0000` 的 EUD COM compatible 状态和 `typec@1500` 均为 disabled。初次按节点名寻找EUD得到空集的只读检查失败保留在 history，已改用实际 compatible 确认；没有发生写入。

只新增该PMIC的 `usb-input@1300`，属性为：

```dts
usb-input@1300 {
    compatible = "realme,rmx1931-usb-input";
    reg = <0x1300>;
    interrupts = <0x2 0x13 0x4 0x3>, <0x2 0x13 0x6 0x1>;
    interrupt-names = "usbin-plugin", "usbin-src-change";
    status = "okay";
};
```

IRQ四元组和名字来自原同机19781 pm8150b.dtsi，不硬编码Linux IRQ整数。4-cell controller沿现有 parent walk 查到；不需要修改 controller、parent、phandle、Type-C、role、PD、EUD 或任何预算。可采用 host-only target-path overlay＋fdtoverlay；若overlay缺少父上下文带来校验噪音，使用原DTB反编译完整DTS、精确插入这一节点再dtc编译的等价静态路径。两种都只生成离线完整 DTB，绝不在运行内核活用 overlay。

必须将新旧 DTB完整解析为 path→property→raw bytes 映射，要求所有965旧节点及每个旧属性逐字保持，只多一个精确 child及上述属性；FDT保留表、`/reserved-memory` 全子树、bootcpu及版本保持。EUD／Type-C disabled再次单独复核。DTB结构／字符串区偏移和总长允许正常编译变化，不能只用整文件SHA不同代替语义核对。保留输入SHA、源码、编译工具／命令／终态、输出SHA、完整语义diff收据。

## ko 构建与配对约束

实际使用原 kernel284 storage helper、显式 Ubuntu/root，进入唯一新私有目录。以原 source-float in-tree 方法建立新 source-view／kbuild；从已精确通过的502私有 source／CONFIG／symvers引入相同基线，原Makefile只加单个obj-m、新C与decoder。仅 `modules_prepare`→`drivers/power/supply/samurai-usb-input.ko`，W=1，保持 release `7.3.0-rc6-rmx1931-samurai-k363+`。没有链接Image或修改旧私有R7、501、502及共享树。

核新ko ELF为AArch64、intree=Y、vermagic／CONFIG保持，全部强导入由502真实builtin exports精确满足（无隐藏模块provider兜底）；modpost／编译无诊断。保留源码、命令、模块及输入前后哈希；所有原 source／build／ko／CONFIG／symvers前后保持。502导出／原501 ABI与CCI补充已有收据复用，不再扫778模块。只验证这次新DT编译、实际parent创建链和新ko链接，不重放IRQ函数测试。

新DTB与新ko是后续成对接入的候选：旧R7的 register_board 路径没有此次去重改动，不能把新DTB单独配旧ko当作已支持。现运行 provider 为 native consumer 保留，不做热卸载。后续固件封装、模块安装、正常重启和实际双IRQ分配／递送均由根单独协调。本叶不以 disabled Type-C、IRQ可分配或供电online授予PD／route／HALT许可，不发APSD命令，也不声称延迟已验收。

## 实际产物和收据

`dt-result.json`：DTC1.7.2＋fdtoverlay实际四个命令各终态0；源9271 DTB保持原SHA。新native DTB为116124B、SHA `13d359c4a78ed423d52f1d5e09345c7dc7032811fabe786952ac11e868adee9f`。965→966节点，3965个已有属性的raw bytes全部相等；只添上述child的五属性。保留表、reserved-memory全树、bootcpu／FDT版本、EUD／Type-C状态保持。

overlay的本地父上下文只重复原有address／size cells供dtc核对，合并后原父值逐字保持。独立overlay缺少SPMI祖先，因此dtc出现一条 `Missing interrupt-parent`；原stderr保留，没有屏蔽警告。合并完整树后没有新child诊断，全部27行旧诊断与原native DTB完全一致；原核实的Linux parent walk可找到4-cell SPMI controller。没有改走完整DTS编译或在运行内核装overlay。

`binding-result.json` 是实际PMIC／OF／provider函数源及DT字节的一致性核对，固定8个实际函数的哈希。它证明可采用的创建／父设备／匹配路径，**不等于真实probe或IRQ已经注册**。

`ko-result.json`：原exec59826终态0，prepare PID1022／28.509秒、ko PID2880／4.227秒，均wait同child且终态0。W=1无编译或modpost诊断。ko为87832B、SHA `7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f`，AArch64／intree=Y／原release，44个强导入全部由502精确builtin exports满足，depends为空，不使用其它模块provider兜底。新CONFIG值及generated autoconf与502相等，旧R7／502／共享跟踪输入前后保持。首次preflight把原共享树不存在的可选vmlinux.symvers当必需，发生在输出创建与compiler之前；旧builder和失败收据留在history，修正为记录其前后均缺失。实际新链接仍只读取502确有、hash绑定的vmlinux.symvers。

私有配套原件位于 `E:/edk2-samurai-out/charging-management-20261023/usb-input-irq-board-private-01/`，包括 `samurai-usb-input-irq-native-private.dtb`、`samurai-usb-input-irq-private.ko`、完整DTS／overlay／stderr。公共叶只保留overlay源、创建链来源和收据，不放DTB／ko或原全树日志。Linux完整模块目录为 `/home/cy122/charging-management-20261023/usb-input-irq-board-01/`。

`pair-manifest.json` 将新DTB和去重ko固定为一组；`delivery.json` 冻结实际工具、源码、命令和终态。当前构建／guard已结束，没有存活make／compiler或卸卷动作。此叶停在离线候选，不改变根已prepared的502通知单改事务。

## 后续实际IRQ接受条件

后续必须在同一个新DT与新provider实例上确认真实probe、两条 `usbin-plugin`／`usbin-src-change` 命名IRQ真实注册，并在真实拔插中核对相应中断计数和事件时间变化，同时保持保护、源预算、native额度及硬件限值正确。两IRQ都为ENXIO／ENODEV时原legacy fallback仍会成功加载并1秒poll，因此模块加载成功或新DT节点存在不能当作IRQ已验收；正常off/on源状态也不能独自证明事件由IRQ驱动。没有本轮实物边沿／时延结论。
