# EUD关闭路由的实际producer仲裁

2026-10-25。在[EFI关闭结果交接](../eud-route-handoff-candidate/README.md)上补真实硬件入口的互斥、引用和撤销。默认关闭，未链接Image、未装机，当前APSD gate仍拒绝；下一步是DWC任务的实际client接线。

不能把`request_mem_region`成功当作排除了后续驱动：当前内核`platform_device_add`可用`insert_resource`包住已有busy子资源，`platform_device_del`也可移走子树。本候选不以资源树形状授权，而是在COM、qcom_eud及earlycon三个实际producer的第一处MMIO/SCM操作前进入同一仲裁器。正常驱动使用真实pdev/物理窗口和devres token，先注册释放动作再创建映射，因而在所有后续资源释放后才交回producer；早期console走不分配的入口。失败probe、释放及重新绑定均保留本boot曾授权的历史，不能重新套用过期的固件关闭结果。

路由provider核本机、真实禁用EUD节点及DWC物理地址，复用真实kernel `next_arg`拒绝早期console参数，拒绝ACPI/chosen stdout通道。只有未出现producer历史且完整EFI交接有效时才发布独占。client绑定真实provider/consumer/context，持引用，lease必须是原对象地址和当前代际；每次begin/validate重新比对交接证据。撤销先封住新请求和旧代际，再在锁外cancel/join。移除遇到join失败时保留独立publication、引用及producer排他，只有后续实际join/end/unregister确认后释放；错误记录不抹除。

目前未证明SoC待机保留路由状态，PM prepare会撤销并join，而且本boot不重新采用旧关闭证据。这一限定不影响普通充电，但尚不构成完整APSD待机恢复支持。不得把此候选、模型测试或reserved页单独当作实际路由授权。

[十二组实际C测试](test-result.json)合入原十组固件/EFI测试，运行完整provider和receiver，使用真实pthread锁、completion、引用及worker join，覆盖来源/对象/代际、早期历史、撤销失败、回调内注销和并发等待。OF、EFI映射和driver core边界由模型提供；不是硬件验收。[源码审查](source-review.json)确认三处claim在硬件操作前、patch零fuzz且其余函数逐字保持。earlycon仅删除一个原本未调用、会触发Werror的旧poll helper；原200us/2ms发送节奏保持。

[首次对象构建](build-result.json)五对象成功，两earlycon对象因旧未用函数失败，原记录保留；[后续结果](build-r2-result.json)复用五个成功对象，只重编修正后的earlycon on/off，并用原源码复现同一warning。默认关闭三producer对象无新导入，真实`__export_symbol_*`两导出存在，复用receiver的私有relocatable接口检查无内部未决。原后处理错误用了旧`__ksymtab_*`名称；只据已完成编译和链接的缓存原件修审查，没有重放构建或伪造子进程收据。共享源码/配置保持；这些对象并非最终固件、Image或模块。
