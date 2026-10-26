# EUD activation 冻结 worker 独立薄审

**在本次冻结 worker 范围内未发现新增阻项。** 这是静态审阅及既有收据复核，不是部署许可或重启成功证明；未读仍在编写的 host controller/独立 fastboot tool，未执行 worker、生成器、设备或旧测试。

审阅对象来自 `charging-session-20261023/eud-boot-activation-candidate`：guard `80c25f12…18a6`、quiesce `311e416b…bc0c`、restart `0fb0948b…6ddf`，contract `f12d65b6…2dec`。`review.py` 只读取、hash、AST parse 和比较源码，`result.json` 记录完整 pins/引用收据；没有导入可执行 worker。

- **旧硬件序列与 tail 复用有据。** quiesce 从 116 行 commit marker 起，归一 work/token 元数据后与固定原 R7 源 `f991d580…17b4` 逐字一致，仍先显式 charging stop，再停服务、核相机资源/DSP/DRM/NV和 taint；不卸载 retained provider。历史 `r7-restart-state.json` 分开记录了旧 quiesce exit0、SSH255、用户 fastboot 屏幕、fresh fastboot 和新 boot。它没有把 SSH255 当成功。新 restart 继承固定 transport-tail 源 `f7cfc985…c615`；独立比较限定增量为新身份/token、全字 CSR 和 claim fsync。
- **新身份没有沿用旧 R7/R6/440 验收。** guard 62–109 行核 fresh guard/旧 boot、SoC raw bytes/DT compatible、release/version#363/rootfs/taint0，固定 R8 manifest 全 installed_files 与三 live notes、helper absent/MaxPower100，以及相机481正式 wrapper。独立读缓存核 wrapper SHA `1c458491…4705` 和 return proof `071c5353…b8e8`；wrapper覆盖当前包、441三模块、468 sensor文件/额外 live note、四 private profiles。return proof 只能作为已交还的来源证据，不能自动检测此刻独占权；worker不锁历史用户PID。
- **完整分区身份有 Image 来源。** guard block_sha 31–43 行只用 O_RDONLY、BLKGETSIZE64 实际长度和完整读取 hash，核96MiB boot为原 a30，64MiB logdump为 `aca01bc2…de8da`。后者是 FAT 分区；kernel365 原 prepare-deployment.py 的 mcopy `::/Image` 原始验证及 boot-package-validation.json 将该完整 logdump hash 绑定 Image363 `15746aab…d6468`，不是靠 uname 或把 boot carrier 当 Linux Image。新 boot `4126a297…bbfcf`、原 a30 与两 FFS 私有包装成功收据相符。未重读大型分区原件或运行打包程序。
- **inspect只读，commit一次。** restart 129–130 行在 /dev/mem open 前退出。commit 136 行仅接受完整32bit 0、1、0x01010101；后者有已缓存 R8 两次只读原件支持，未扩成“低byte1均可”。138–144 行先以 x 独占 claim、绑定事务/boot/token/request_count1，并 fsync 文件与父目录，才 freeze。已有claim在guard和exclusive创建两层拒绝重放。
- **断 transport 不阻断确认 CSR 后的尾段。** 147–151 行 unbind后要求driver消失，完整写0并要求完整读回0，随即一次 RESTART2 bootloader；中间没有 print、JSON、sleep 或 mmap close。旧8例实际 CPython pipe/真实try体边界收据含 BrokenPipeError、失败readback与syscall返回路径；新18 guard＋7全字CSR/claim病例的收据与实际字节吻合。本审未重跑。它们的MMIO/OS/syscall边界是fake，不是新实机验收。

执行仍依赖外部 root 的实际独占交还、原key固定传输及新事务目录。按contract只启动一次 detached worker，restart日志应在已核tmpfs `/run`，不能依赖SSH stdout。当前 worker guard中的assert需由正常未优化Python执行；host controller具体环境/launch策略不在本次薄审范围。

`filesystem_frozen_restart2_armed` 是 retirement/syscall前记录的意图；SSH断开可能发生在 EUD 关闭时，二者都不能证明进入bootloader、写入boot或新boot。未知结果只能沿原进程/状态及fresh主机证据处理，不能再发restart或自动接回EUD。fresh唯一fastboot serial/product/partition和后续写动作由独立tool另核。

成功重启后 tmpfs `/run` 本来可能消失，**不应要求事后取回不存在的最终日志才确认完成**。完成应依据同事务的已有派发claim、fresh fastboot及后续原key/新boot UUID/软件与硬件状态证据。syscall若返回，worker只thaw并失败，不伪装恢复已停服务/EUD；局部停机失败同样需root读实际状态后决定，不自动重跑。

本叶没有确认实际CSR0、fastboot枚举、新boot、panel、EUD路由、SDP500或图标收益；没有设备/SSH/USB/SDK/Git操作，没有修改作者冻结目录。
