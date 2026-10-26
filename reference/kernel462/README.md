# 462 r1：前摄共享 route／reset／MCLK 的受限代码候选

已形成[三文件补丁](0001-media-imx471-use-shared-route-and-reset.patch)，并在独立稀疏source-view／私有生成O中，以Image363配置为输入完成 `imx471.o` 和板DTB的j2构建。[构建收据](target-build-r1-validation.json)、[实际C状态迁移](resource-c-validation.json)、[binding及原provider核对](binding-provider-validation.json)通过。**r1仍为NOT deployable：runtime故障保留route已实现，但probe/remove后的活跃devres引用隔离尚未完成。**没有手机／SSH／SDK／DT部署，未改共享source354或453／455／456缓存。

候选完整源与产物仅在私有kernel462；IMX471 C SHA256 `11e88b65…dc0c92`，DTS `226790fe…4fb43b`，binding `c1a64d9a…ad8ca`。本轮未生成KO、Image、rootfs或全模块；不以对象编译代替可加载模块／硬件验收。

## 已落到代码的所有权

保留[454共享资源事实](../kernel454/MUX-NEXT.md)和[458时钟限制](../kernel458/CONSTRAINTS-NEXT.md)。route使用现成gpio-mux，GPIO29只有该provider持有；前摄通过标准mux-states选择state1，用try_select持有整个有电区间。GPIO12改由reset-gpios fallback去重出的单一reset-gpio provider持有，consumer使用exclusive_released、acquire／assert／deassert／release。没有另造路由或reset框架，也没有创建不受现有驱动支持的reset DT compatible。

前摄DT删除default/sleep共享pinctrl和assigned-clock-rates；驱动core在probe前选pin状态的旧写入口已被移除。GPIO mux provider永久配置共用MCLK引脚，GPIO29／12只有pinconf，没有pinctrl output-high／low；MCLK2频率仅在已经取得route后设置，enable引用仍走CCF。前摄probe第一阶段先取得route，再检查时钟／获取reset／供电；runtime power_on/off走同一routed路径，旧非routed板路径保留。

GPIO mux和reset provider自己的首次初始化早于consumer可使用它们，因此**该DT迁移必须在旧消费者全部停止的quiescent启动下实施**。gpio-mux首次获取GPIO会设置低态，reset-gpio首次probe会assert；不能把新provider热叠加在仍运行、仍直接持有GPIO／pinctrl的旧IMX471上。新消费者必须等共同provider ready后才可供电。首次初始化阶段不冒充已被consumer租约包围。

第五OV02节点没有添加。PHY2继续只有前摄的四lane静态endpoint；本轮没有解决CAMSS双输入mutable link／逐输入lane配置，不能据共享route补丁宣称未来单lane OV02已经可用。它的PIXEL_RATE／LINK_FREQ仍按458缺口处理，没有猜测值。

## 已执行验证

`imx471.o` 94320字节、SHA256 `a2571a9a…850c9`，W=1／-Werror无C诊断。DTB115629字节、SHA256 `1cd47db3…62aaec`；DTC保留DSI和PM8150B处两条avoid_unnecessary_addr_size告警，不能称整板零告警。未复制或链接巨大vmlinux.o，未复制整个source／O；构建前后可用空间均不少于2GiB。

实际候选的routed C函数逐字提取后在宿主API模型执行，ASAN／UBSAN通过16例：正常周期、peer busy与完全断电后接班、9个power-on失败点、4个power-off失败点、尚未供电的probe-route释放。模型检查成功引用的取得／回收顺序；不是电压、GPIO、电源故障或内核并发实测。runtime关闭失败时剩余rail／clock／reset状态保留，禁止重复power_on、route不deselect；恢复只处理剩余成功引用。

现有dtschema通过修改后的IMX471 binding文档检查，定向验证sony,imx471、gpio-mux和mux-controller均零诊断。FDT核对前摄没有自动shared pin／assigned-clock属性，route为唯一GPIO mux，reset12仍对应同一GPIO spec，OV02节点不存在。

## Provider确有匹配原件，尚无本轮现场ready证明

Image363嵌入配置为 `CONFIG_MULTIPLEXER=y`、MUX_GPIO=m、RESET_GPIO=m；实际Makefile按MULTIPLEXER编入mux-core，所以不能因可见菜单项MUX_CORE未选就称core缺失。新对象的内核API导入均能在原363 Module.symvers找到；`__this_module`是未来mod.o提供的本模块元数据，未当作内核导出。

只从已钉SHA的363模块tar提取两份原件：mux-gpio.ko为9112字节、SHA `711b222d…33182`，reset-gpio.ko为7704字节、SHA `f5d136e8…c1b6b`。二者均匹配363旧安装inventory、intree、vermagic及实际导出；modalias分别为gpio-mux OF和auxiliary:reset.gpio。原363 postboot收据曾核过全778安装SHA，因此不用重新构建provider或Image。

这些是现成可复用包及历史安装证据，不是本轮手机当前文件／加载证明。真正迁移前仍须在授权窗口核实际内核、这两文件和模块加载、辅助reset provider的probe／autoload；不能仅凭API和schema宣布新DT能够probe。原件缺失时的局部目标仅为 `drivers/mux/mux-gpio.ko`、`drivers/reset/reset-gpio.ko`，配置和ABI门槛仍相同。

## r1的确定剩余缺口

`route_selected`和已成功引用的mask能阻止runtime错误路径过早交出route；**它们不能阻止driver-core在probe失败／remove返回后释放devres**。r1会留下锁并报告不完整关闭，但reset／clock／regulator句柄仍可能被put，且传感器对象本身为devm分配。这不是完整隔离至重启，也不是任意故障下安全卸载。对应普通get／put、设备与模块引用和独立holder需在r2单独处理，不能覆盖r1源／产物／日志。既有打开FD跨解绑的对象寿命问题同样未由此补丁解决。

冻结r1后仅允许创建独立r2副本。后续硬件前置仍是：完整异常引用隔离审查、生成匹配可加载模块、冷态DT切换与回退、先前摄独用及冲突拒绝，再考虑第五节点；本次没有取得这些硬件结论。
