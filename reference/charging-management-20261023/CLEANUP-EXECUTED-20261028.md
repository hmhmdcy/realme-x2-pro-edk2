# 2026-10-28 旧构建卷清理回执

本次只删除已由旧 cleanup ledger/verification 明确记录为可重建、已校验，
且没有任何当前充电适配脚本或证据 manifest 引用的构建卷和可重新下载 ISO。

保留：

- `cleanup145/cleanup-ledger-*.json`
- `cleanup20261019/*-private.json`
- `rx61/session-61.md`、下载/校验/HEAD 回执和源码材料
- `kernel282/*.json`、`*.log`、配置和结果回执
- R15、r20、原厂备份、分区/NV、当前源码和模块

删除目标：

- `kernel282/full-kernel-build282.ext4`：32.00 GiB，旧完整构建卷。
- `cleanup145/volumes/*.ext4.zst`：27.19 GiB，5 个已校验旧构建卷。
- `cleanup20261019/kernel118-current-build-volume.ext4.zst`：4.89 GiB，
  已验证的旧 kernel118 构建卷；与 145 版本的哈希不同，不再使用。
- `rx61/EWDK_ge_release_svc_prod1_26100_250904-1728.iso`：18.64 GiB，
  可由 Microsoft 重新下载，下载/校验回执保留。

预计回收约 82.72 GiB；实际值以删除后 `Get-PSDrive E` 为准。
