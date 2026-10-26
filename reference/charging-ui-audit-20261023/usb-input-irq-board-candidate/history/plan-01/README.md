# USB input IRQ：板级接入最小计划

本叶先交方案，尚未编译新 DTB 或 ko。只复用已冻结 IRQ provider（C `0fdafb8b…34b7be5`、FLOAT decoder `a17caa2c…56d548fd`、16例及独审），不再修改驱动算法、不重跑旧16例。没有手机、桌面、SDK、Git、共享 source/build 写入，也不做 firmware 封装／安装／重启。

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

待根确认方案后，使用原 kernel284 storage helper、显式 Ubuntu/root，进入唯一新私有目录。以原 source-float in-tree 方法建立新 source-view／kbuild；优先从已精确通过的502私有 source／CONFIG／symvers引入相同基线，供给原Makefile加单个obj-m、新C与decoder。仅 `modules_prepare`→`drivers/power/supply/samurai-usb-input.ko`，W=1，保持 release `7.3.0-rc6-rmx1931-samurai-k363+`。不链接Image或修改旧私有R7、501、502及共享树。

核新ko ELF为AArch64、intree=Y、vermagic／CONFIG保持，全部强导入由502真实builtin exports精确满足（无隐藏模块provider兜底）；modpost／编译无诊断。保留源码、命令、模块及输入前后哈希；所有原 source／build／ko／CONFIG／symvers前后保持。502导出／原501 ABI与CCI补充已有收据复用，不再扫778模块。只验证这次新DT编译、实际parent创建链和新ko链接，不重放IRQ函数测试。

新DTB与新ko是后续成对接入的候选：旧R7的 register_board 路径没有此次去重改动，不能把新DTB单独配旧ko当作已支持。现运行 provider 为 native consumer 保留，不做热卸载。后续固件封装、模块安装、正常重启和实际双IRQ分配／递送均由根单独协调。本叶不以 disabled Type-C、IRQ可分配或供电online授予PD／route／HALT许可，不发APSD命令，也不声称延迟已验收。
