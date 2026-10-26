# 365：静态 ICP／板级固件内存引用，以及未生效的 FAT DT 更新

364实机确认：overlay对已有无phandle节点的标注不能供实时OF解析。新增静态SoC `icp@ac10000` 描述已对照原厂的19时钟、四MMIO、IRQ、复位、三电源域、SMMU流和CAMSS供应者；Realme板级单独给出`memory-region = <&camera_mem>`，现有9ab00000/5MiB/no-map不变，ICP保持disabled。没有把机型物理地址塞进公共A5驱动。[源码补丁](static-icp-board.patch)。这是本地bring-up描述，尚无启用生产ICP的完整平台驱动／上游binding验收。

只编译DTB，零诊断；新增一个disabled节点、为现有固件内存节点生成phandle。DTC重排207个引用单元；逐项确认所有引用目标路径保持、其它已有属性语义不变。[构建和语义核对](dt-build-validation.json)。首版验证工具误以为已有数字phandle不会重排，已改为按目标路径检查，没有放行其它属性变化；没有因此重复构建内核。

保留Image363、778模块和362用户空间，只更新logdump FAT中的DT文件。一次正常停服务、logdump刷写和启动后分区读回完全一致，但运行中没有新增ICP节点，固件预留区仍无phandle。该DT更新**未生效**：[实际启动](postboot-validation.json)。当前EDK2使用固件卷内DT；FAT文件存在和正确不能作为Linux实际DT已经更新的证明。

此失败保留，未执行依赖新引用的A5 CPU实验。366复用既有EDK2 DT-only构建流程，将同一份DT放入真正交给Linux的固件卷；Image/模块/用户空间无需重建。
