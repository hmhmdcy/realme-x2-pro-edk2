# USB IRQ／保护查询配套包：根独立薄审

已读最终封装器、7项受影响检查及实际物化收据，直接重读两个私有压缩包和新旧清单，未调用作者构建/测试入口。[review-result.json](review-result.json) 通过，作者delivery `3d5b78bc…2a07b`的13个文件完整匹配。

正向包严格为两ko＋manifest，51736B；回退包严格保留原R7 USB、原R8保护和原清单，44194B。两包均为原路径的root regular 0600文件，无额外服务/桌面/分析器。清单仅两模块的四处SHA和revision共五处差异；所有其它字段原样。实际包内四个新旧模块的AArch64/intree/完整build-id note与cohort一致。根另直接核对新保护ko、完整note及实际nm的31个强导入，全部由真实502 builtin exports满足。

新IRQ boot/DT必须与新USB ko成对，底层为502载体。既有manager614不读取revision，但启动前新磁盘/旧驻留不能当运行态一致；仍需独立事务、guard、正常停充和重启后的真实notes。不得混入prepared的502只写logdump事务，回退不盲降一个已adopt的502 logdump。

限定范围未发现新增阻断；没有重复7项、驱动旧套、内核构建、设备或SDK操作。本审查不证明实际加载、双IRQ递送、图标时延、新2719语义或整机PM通过。
