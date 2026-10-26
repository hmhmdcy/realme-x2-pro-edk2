# Image501 repro 构建与元数据独立薄审

只读检查冻结 runner、元数据比较器、363 基线和501构建/ABI收据，并用本叶的独立读取器核对已存在的私有产物。没有运行 runner、ABI工具、函数测试、编译、挂载/helper、设备/SSH/SDK或Git。Image 为 `3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02`，59243008字节；本轮不是启动、模块实装或相机验收。

363 baseline 从固定 ba61 blob 导出源码，与当前 HEAD 5b0 明确分开。其实际收据同时核原 bq.o、CONFIG、vmlinux、Image 的原 SHA，所有 archive/link 输入与共享三树、Git index及父 namespace/挂载保持。B501 再从该逐字复现的独立基线复制，没有直接将当前可变共享 build 重链冒充单一改动。

候选源保持冻结 B SHA `0aa3c533…fd88ffe`。源码中的 static bool 未初始化、参数权限0444；独立读取实际 bq.o 的 ELF symbol 显示 `samurai_instant_current` 是1字节 `.bss`/NOBITS，默认零。未改 bootargs。归档的两片变化为 bq.o 和 init/version.o，其余3245叶、32个libstub保持；init/version-timestamp.o 是额外最终链接身份输入。kallsyms和vmlinux.o的变化是链接派生产物，不能说全部 `.o` 只变两件。

两个实际 version ELF 的全部原始字节，都精确等于仅将两处 `#363 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026` 替换成 `#501 ...` 的结果；每对象只有6个不同字节，section headers及可执行 sections相同。变化只在 `.data`/`.rodata`，没有通过回写二进制“修补”差异。时间戳明确是原可复现时间戳，实际编译UTC另记，不能称它为实际编译时间。

独立核对原/新 CPIO、gzip输入、usr/initramfs_data.o 均分别为 `fc1d2772…14c9669`、`319b665d…4b81678`、`25244378…07484de`。候选 Image 内嵌 CONFIG 解压后为原 `23e088a9…f30ed`，与候选 `.config` 相等；不混用共享当前 e48f 配置。具体实际字节核对见 [artifact-readback.json](artifact-readback.json)。

ABI 收据 `3ed8fc61…7ac25c` 绑定实际 ELF 的15097个导出名及原 symvers整行（含类别/namespace/CRC）、原778缓存模块及正式481四件加7件依赖，共11件缓存检查。CONFIG/release/公开headers/非gauge叶保持，支持本次修改的静态兼容边界。MODVERSIONS关闭的零CRC不是独立类型ABI证明；缓存检查也不是新内核加载证明。原ABI因卷回收失败的收据保留，后续只读ABI终态0与实际构建终态0分开记录，没有因此重编。

原 ABI 审计器允许完整原 Module.symvers 加当前 group 的较宽集合，不能单凭该算法排除被替换的旧提供者。已由独立补充叶 `gauge-image501-abi-provider-supplement` 的逐 symbol 映射闭合这一范围：11件实际当前 ELF 只需候选内建导出、当前11件导出和精确保留的 v4l2-cci.ko。只有 sensor 的4个 CCI 导入需后者；从原模块 tar 读取的 CCI 与原 inventory SHA `232c5140…34e705` 一致，实际 ELF 导出覆盖4项，CCI 自身导入也闭合。补充结果 `db8dffd5…483d2` 不再使用 all_old_names 回退，原 ABI/delivery 保留历史。限定构建/元数据/静态 provider 范围未见阻项；仍不宣称类型ABI全证明或新内核实机通过。
