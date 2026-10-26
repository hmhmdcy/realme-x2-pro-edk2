# IRQ配套版本：只读新启动验收组件

本叶补足未来[两ko＋清单配套包](../../charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/README.md)的设备侧验收，派生自已冻结的502 collector。当前只有只读设备组件，**没有真实request、新guard、传输、启动或adoption**；也没有修改当前501或prepared502事务。后续host必须先重审真实stage/启动原件、同child终态及原密钥endpoint，再绑定请求；不能把离线fixture当现场许可。

原collector的21个函数逐字复用，包含实际板型/rootfs/新boot身份、SDP/CDP预算、Full与瞬时NOW/AVG、正式481/468相机、用户服务/remoteproc/故障及EUD生产者检查。只改变collect、完整载体/安装检查、audit组合和新schema入口。新增收集始终在实际新启动身份门之后，只读取普通sysfs/DT/proc；完整boot/logdump仍以O_RDONLY流式核对。无CSR、裸I2C、capture、充电/服务控制或guard/pointer写入。

## 新身份与真实中断实例

新boot必须为IRQ boot `eddadec3…f6e06`，logdump保留502 `ace2e261…63ed1`；实际内核仍#502。新manifest为 `5fca8e5a…69417`，同时要求解析后的全部字段精确等于实际配套清单，不能仅凭一个文件SHA快照就接受另一份缺字段的manifest_text。USB／保护disk及驻留note均必须是新版本，原charger不变，staged期间旧驻留不能通过本检查。

`irq-evidence.py`被原样嵌入设备源码，供以后有限边沿观察复用。它要求power_supply的真实device绑定 `samurai-usb-input`，of_node正是PMIC2的 `usb-input@1300`，且全部platform设备中只有同一个实际bound provider。五条原厂DT属性逐字核对，包括两个4-cell IRQ、名字、reg和okay状态；旧software provider不算新实例。

`/proc/interrupts`必须显示两条不同Linux IRQ及唯一命名action `usbin-plugin`、`usbin-src-change`；缺一条、两条均缺而退回poll、重复/共享action或格式不完整均拒绝。中断号由实际domain决定，不写死Linux IRQ整数。静态新启动可以两条计数都为0：这只证明已注册，不证明已递送或图标更快。

计数按每个CPU保存，前后CPU集合或IRQ映射变化时不比较总量；任何CPU计数回退也记不可比，不能让热插CPU产生假增长。两快照必须处于本次采集区间且不重叠。计数增长单独记录，`physical_delivery_accepted`和图标/实际IRQ递送验收始终false；必须结合之后真实拔插窗口、对应状态变化和独立时间原件，才能讨论物理事件因果。这个检查不授予APSD/route/PD权限。

## 已完成与下一接入

[test-result.json](test-result.json)：27个受影响案例及默认入口实际rc0，旧矩阵未重跑。完整audit输入复用实际501保存原件，明确合成新502/cohort/IRQ身份；验证静态注册、精确清单、新旧驻留差异、旧boot拒绝、缺/重复/共享IRQ、CPU与计数边界、OF实例、时间区间及错误阻止整体验收。没有模拟硬件、执行collect或创建真实stage材料。

仅本地检查（WSL/Linux，无设备访问）：

```sh
python3 -B device.py --check-local
```

未来入口使用独立 `samurai-usb-irq-protection-postboot-readonly-v1` schema，要求 `usb-irq-protection-stage-*` 的真实终态 `staged/runtime_pending`、all_new_fsynced、stop_verified及旧新manifest身份。其hash和源boot事实必须由host对原始stage材料重审后绑定；单纯正则形状不是来源认证。当前不会生成这些值，入口拒绝无request执行。真实新boot仍须不同于stage旧boot；#503 DWC候选不能套此#502配套版本。

后续还需独立boot激活上下文和host请求封装，再做真正probe/IRQ/保护与预算检查。此设备组件没有把整个未来部署流程宣称为已就绪或已验收。
