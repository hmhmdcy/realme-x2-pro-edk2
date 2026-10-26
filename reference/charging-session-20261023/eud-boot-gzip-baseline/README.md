# 原 a30 gzip/payload 基线通过

仅执行一次 `/usr/bin/gzip -c`，无filename argv，fd0为私有regular raw文件；host Linux PID812，宿主exec/tool均exit0，stderr为空。原 Android v1 ID在工具运行前已核实，原144-byte shim+已通过compact FD的7340176-byte raw逐字等于a30。

stdin fstat记录 regular、size7340176、mtime_ns1792719172000000000。工具输出的完整6229964-byte gzip（含头 `1f8b080044b9da6a0003`、DEFLATE、CRC/ISIZE）逐字a30，SHA `b8deffe8c707c6a2541010dc9351f27abe5de1617a8d18f24f26b430f90c65d7`；追加原450826-byte compat后的6680790-byte fullpayload也逐字a30，SHA `44625abd2985df2d11bd47dea7141ce3284cdc7759485247f8b8f65f3fefe982`。没有头修补或字节宽免。

144个父输入及完整mountinfo前后保持。`run-gzip.py` SHA `86db76d8304ee0ad164c09b20c8e4dc2d5ae641c09a3d819bf625db39603726f`；私有目录 `E:/edk2-samurai-out/charging-management-20261023/eud-boot-gzip-baseline-private-01/` 已有终态，拒绝重放。完整私有result SHA `3de516c86a7ca1d2fcb6069741aa253c7470f844bd2e809d6969ceb1f9733632`；本目录 `result.json` 是简明公开收据。

未重跑FV/FFS/压缩层，未生成新boot，未访问设备/SSH/USB/PM/SDK/Git/NAV，未部署或重启。下一步的两FFS候选执行器位于同级 `eud-boot-two-ffs-candidate/`，默认只读，须根会话和独立审阅后另行批准；本基线不证明候选启动、EUD关闭或USB500成功。
