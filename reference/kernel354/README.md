# 354：ICP DMA 别名映射后端及真实 SMMU 探测通过

2026-10-20。上一轮353实现A5队列/ELF核心，本轮补上实际内存后端，并在手机的Apps SMMU上验证IOVA0..5MiB映射和完整释放。没有启动A5/原厂固件，没有更改持久DT或已安装模块。完整多摄/ISP目标保持active。

新增`camss-icp-a5-memory.c`与四个生命周期API：分配、映射、撤销、释放。先要求默认DMA域和明确覆盖0..5MiB的`IOMMU_RESV_RESERVED`，再分配32bit IOVA的一致性RAM，清零后逐页翻译原DMA地址并建立A5地址0开始的别名。不假定物理连续，也不把32bit IOVA限制错误套到物理页地址。整个生命周期由拥有设备的驱动串行，并在停止A5后撤销。

目标区已有映射时拒绝覆盖；映射中途失败会撤销已建立的前缀。撤销按倒序执行，发生错误时保留准确的剩余前缀，拒绝释放仍被A5地址引用的RAM，允许重试；设备被切到别的域时拒绝继续操作。没有改IOMMU框架或强行导出内部`iommu_get_dma_domain`。接口依赖353已核的导出API。

主机/AArch64各25项实际内存后端函数检查通过：1280个离散且高于4GiB的模拟物理页、coherent/noncoherent属性、缺少/错误保留区、错误DMA域、错误IOVA、分配失败、首/中/末页映射失败、物理页缺失/未对齐、已有外来映射、撤销失败后拒绝free与重试、域切换等。[检查结果](memory-validation.json)。这些API桩不冒充真实SMMU。初次测试工具的stdio命名冲突、缩进告警及保留区桩的生命周期已修正，生产内存后端没有因此降低错误处理。

为实机使用，将核心及诊断源码真正接入隔离内核工作树`/mnt/samurai-full282/source354`，父提交为348的`30086bae...`，提交`ea71fa4fd8375502d73231dfb749cbd3a23920eb`，8文件、tracked clean。[源码状态](source-state.json)、[完整补丁](a5-icp-core.patch)。现有CAMSS、传感器和Image未改。本轮新增两个隐藏Kconfig项，正常配置不会自动开启内存诊断。

实际in-tree候选以W=1/-Werror构建两个模块，最终r2耗时13.85秒、无诊断：核心122976字节、诊断73464字节，vermagic匹配现机7.3.0-rc6-k298，Kbuild自然记录intree=Y。[构建](intree-build-validation.json)。核心与R1字节完全相同，R2仅更换诊断内嵌的临时覆盖。共享camera输出和config/关键生成文件已恢复；构建中刷新的host tools和其它准备输出未回滚，未称整棵build所有字节不变。

实机前读取当前启动身份、内核和SMMU：原boot guard匹配，Apps SMMU phandle44、两IOMMU参数，OF_OVERLAY/DYNAMIC均可用；ICP两个叶时钟enable_count均0。诊断只给新增的临时设备使用原厂A5固件SID0x2222，probe先检查IOMMU组只有自身，避免操作已有设备的域。[当前前提](runtime-prerequisites.json)。没有停PW/WP、重读EEPROM或做无关软件包检查。

R1临时核心加载成功，但设备树覆盖加载返回EINVAL。日志明确是当前DTB没有`__symbols__`，而DTC `-@`生成了不需要的导出节点；尚未执行内存映射。核心已卸载、临时节点不存在、taint0/相关故障0。[保留失败](memory-runtime-r1-validation.json)。改为plugin覆盖不导出符号，保留`__local_fixups__`；引用既有SMMU用实测phandle，因此无需修改或重刷基础DTB。

R2 worker4723已终态退出。临时覆盖及诊断成功：组内1设备，一致性RAM分配成功；1280页（5MiB）A5别名逐页与原DMA映射对应，CPU页首/尾模式保持；别名存在时另一次DMA分配仍避开保留窗口。全部1280页随后撤销并逐页确认无映射，backing释放，最终mapped_bytes0/backing_owned=false。测试核心/诊断模块及两个DT节点均已移除，taint0→0、相关故障增量0。[实际结果](memory-runtime-r2-validation.json)。

这是实际SMMU映射及CPU内存生命周期证明，尚未让A5从中取指或执行DMA，不能称固件已运行或真实ICP缓存一致性已完成。临时DTBO、DMA地址、原始日志和模块仅私存；公共报告不含backing DMA地址。无活动probe/build/SDK bind。

层次划分：新增SoC A5内存后端，运行时诊断覆盖只验证该SoC设备的映射条件；持久板级DT、传感器、主线IOMMU和用户空间IPA均未改。纯IOVA节点经运行时覆盖验证，永久DT的schema和早期保留区扫描仍待后续适配。现机继续沿用349最后观察的338/r27/r22＋344私有默认，未安装本候选。

下一步355实现A5平台资源、电源/时钟、IRQ及HFI启动握手，结合原厂A5/ICP硬件管理器核对BPS/IPE上电顺序后再运行固件；随后接会话、IPE IO/IQ与libcamera m2m。350～352恢复的Gamma/LTM/前摄矩阵仍未成为新默认，曝光表、防频闪、更多模式、正常照明光学、几何同步和连续AF仍待。
