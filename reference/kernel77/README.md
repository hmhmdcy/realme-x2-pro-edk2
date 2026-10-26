# kernel77：BQ28Z610 真实读取与显示启动回归

日期2026-10-10；手机仍用 #76 Image。详见 ../../sessions/77-bq28z610-live-gauge-and-display-regression.md。
已只刷boot接入标准只读电量计；两个启动45样本与sysfs单位对应。首次显示接管出现
DSI下溢，开关屏后恢复，仍需定位。充电控制没有接入/验收。

| 文件 | 用途 |
|---|---|
| hardware-validation.json、日志及样本 .txt/.gz | 完整捕获SHA、两启动45样本、显示/GPU回归及明确的首次启动失败 |
| candidate-validation.json、firmware-validation.json、dtb-validation.json | gauge-only DT、固件FV/FFS及Image/config/logdump保持 |
| final-device-state.txt、gauge-flash-validation.json、recheck-reboot.json | 设备最终状态、仅boot写入和第二次仅重启 |
| sources-before.json、sm8150-samurai.dts.after、gauge-dts.patch | 源码保留摘要及精确DT增量 |
| read-gauge.c、build-reader.sh | 固定地址/12标准字的组合只读事务；无MAC、解封、NVM或寄存器数据写入 |
| run-gauge-tests.sh、run-recheck-samples.sh、validate-samples.py | 实际连续读取、已完成回归及离线核验 |
| prepare/build/flash/reboot/verify 脚本 | 本轮受限部署过程；含一次性备份和新输出前缀保护，不可原样覆盖重跑 |
| patch-validation.json、0013*.checkpatch.txt | 精确应用及checkpatch零错误/警告 |
| SHA256SUMS | 本轮文件封存 |

本地产物：E:\edk2-samurai-out\kernel77。回退 boot-before.img 即 session75已验收
boot，logdump保持原样；两个摘要见session77。私钥、CPIO、专有固件、完整镜像不发布。
