# B501 ABI provider 集合窄补充

本叶只补原ABI检查中 `all_old_names` 过宽的集合范围，不改已冻结501/ABI/delivery，也不构建、挂载或访问设备。真实只读 exec session5746 终态0。

实际11件当前ELF中，10件的全部强导入由候选15097个builtin导出与当前11件exports闭合。sensor的4个非builtin导入 `cci_multi_reg_write`、`cci_read`、`cci_write`、`devm_cci_regmap_init_i2c` 仅需保留的 `v4l2-cci.ko`，不是已替换的旧cam provider。

该CCI从原363模块tar（SHA `fca01dab…fb8f73b`）仅在内存读取，逐字匹配原inventory SHA `232c5140e5bb7f8058bcb103822a9c643e12b5fe60acf8fe2fd17dc58234e705`；它不在481显式替换集合内。实际ELF确实导出上述4项，其自身强导入也由builtin闭合，无须旧778导出全集。各符号的精确provider映射在 `result.json`，本结论限现有缓存和已知保留身份，不新增运行态认证。

`result-without-retained-cci.json` 保留对照：直接去掉旧导出全集时，仅出现这4个CCI需求。加入这一件精确保留提供者后，全部11件没有未解析强导入。没有重跑其它已过项。
