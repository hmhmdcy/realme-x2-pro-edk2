# 462 r2：独立的 routed-resource holder

r2补齐r1已识别的consumer devres缺口：前摄走共享route时，mux／reset／clock／三路regulator句柄由独立分配的holder以普通get／put持有。probe失败或remove时如果关闭失败，holder及其设备、模块和全部资源句柄保留，并拒绝同device重新probe。**r2仍为NOT deployable**；新mux接口需要更新内建内核，当前没有生成Image或KO，也没有手机／SSH／SDK／部署。

[r1](../README.md)的11份文件、原三文件候选和对象／DTB保持冻结。本目录仅存r2增量补丁和验证；完整候选源、稀疏source-view、生成O及原始日志在私有kernel462/r2。依次应用r1补丁、[非devm mux接口补丁](0001-mux-export-unmanaged-state-handles.patch)、[holder增量补丁](0002-media-imx471-retain-resource-holder.patch)。r2不改r1 DT／binding，不增加第五节点、未知时钟值、PHY endpoint或光学参数。

## 实际API差异

363匹配的mux-core只有devm mux-state获取入口；内部四参数mux_state_get和mux_state_put原为static。非devm mux_control_get读取mux-controls，不读取含固定state的mux-states，不能直接替换。r2保留内部解析和原devm语义，增加公开两参数mux_state_get及mux_state_put；consumer.h同时修正MULTIPLEXER=n分支原先与末尾宏不对应的devm声明。

新接口得到的仍是实际mux-chip device引用。它不会阻止supplier解绑，也没有给gpio-mux模块增加owner引用；r2没有把设备引用冒称为供应商devres永久保护。reset_control_get_exclusive_released的core会取得reset provider的device及module引用；clk_get会取得clock core的kref及owner引用；regulator_get会取得regulator device及owner引用。这些引用在失败detach中均不put。

## holder的持有与回收

| 阶段 | 实际行为 |
| --- | --- |
| probe初期 | 独立kzalloc、get_device、加入去重list；先取得route，随后获取reset／clock／供电句柄。共享引脚或时钟变化仍在route取得之后。 |
| 取得route | try_module_get在select之前；竞争失败释放本次module pin。模块已GOING时拒绝开始。 |
| 运行关闭失败 | 保留route及剩余成功enable／acquire状态，拒绝再次power_on；仍绑定时允许关闭重试。 |
| probe／remove的detach失败 | 标记removing并永久留在holder list；不释放任何资源句柄、设备引用或power-module pin，无自动重试worker，同device重新probe返回busy。 |
| 完整关闭 | clock停用、reset assert、逐路disable、reset release，随后deselect；只有全部成功后才能put句柄并释放holder。 |

holder从未注册为sensor devres。sensor本体仍为原devm对象；即使其probe失败／remove收尾释放对象，也不会释放留在独立list中的holder。remove在PM disable／barrier之后detach；早期probe错误则发生在PM尚未启用之前。新holder的mutex串行化其power操作，构造阶段也按同一锁约定取得route。

## 已执行的受影响验证

[holder实际C收据](holder-c-validation.json)通过35例ASAN／UBSAN宿主检查，逐字提取候选holder C：9个分配／获取故障、9个resume上电故障、4个runtime关闭故障，以及4个detach关闭故障场景。后者确实保留独立对象、device／module pin和全部get句柄；模拟sensor devres已释放后仍阻止重新上电、同device重probe及peer取得route。四个永久隔离场景使用独立逻辑mux模型，避免将四次启动误作同一次硬件会话。

[mux接口收据](mux-api-validation.json)通过4种实际C结果：成功、provider延迟／错误、缺失和内存分配失败；取得／回收引用平衡。内部解析及put算法与原件逐字等价，五个原managed入口／release逐字未改，devm通路仅内部helper改名；实际consumer.h的关闭分支也经宿主定义编译。宿主模型不是内核OF解析、硬件供电、lockdep、PM并发或实际卸载测试。

[最终对象构建](target-build-r2-validation.json)以Image363精确配置为输入，在全新r2稀疏source-view／生成O中完成j2、W=1／-Werror构建：

| 产物 | 字节 | SHA256 |
| --- | ---: | --- |
| imx471.o | 104168 | f53441db91121c7cf26c4ff526fd5aa88425fa7828a5af0fd91bc5c2287a00a8 |
| mux/core.o | 70496 | cd1022c3e0a346b3ad6414a62205741aef0c1a0286045accdbb78270cb8972b2 |

无编译诊断；mux对象确有两个__export_symbol记录，IMX471相对原363缺失的新增导入恰为mux_state_get／mux_state_put。MULTIPLEXER=y使mux-core为内建；**旧363不能靠替换IMX471模块获得这两个导出，后续需要新Image**。未复制／链接巨大vmlinux.o，未复制整套source／O；构建后可用空间6.38GiB。最终候选C为42f2c8e2…b1e496c，core为b4eb7a8a…e20c66，header为1029dc98…54d51。[冻结收据](r2-final-validation.json)记录完整SHA、配置差异及r1不变核对。

初版r2对象／收据保留为历史；最终版本仅补构造阶段route_get的mutex约定，并重跑受影响holder检查和对象构建。r1结果没有被覆盖。

## 保留的准确边界和下一步

本轮只修consumer主动释放devres的确定缺口。所有supplier必须保持绑定；原gpio-mux没有suppress_bind_attrs且其句柄不pin owner，不能宣称任意supplier强制解绑、parent controller删除或provider模块卸载仍隔离安全。现有gpio-mux set也不把GPIO写入的底层失败返回consumer，因此API引用状态不等于物理引脚成功证据。clock disable等void API和PMIC部分失败同样没有被宿主模型证明。

旧IMX471打开FD跨unbind的sensor对象／V4L2控制状态寿命不由资源holder解决，不能据此宣布可任意解绑／卸载。下一次实现或验收前先处理这条现有sensor生命周期边界，并组合已有V4L2 core寿命修复；不要将455 lens对象布局直接复制到sensor。

待这些边界完成并安排可回退的新内核／冷态DT窗口后，仍需先核前摄独用、共享竞争拒绝及停流完全断电，再考虑第五摄像头。[r1 provider原件](../binding-provider-validation.json)和DT／binding结果按相同输入复用；本轮没有重新取得现场provider-ready、物理route／reset、时钟、第五timing或长稳结论。
