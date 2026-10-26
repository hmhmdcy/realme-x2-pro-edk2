# EUD boot-only 激活工具候选：纯离线，未执行

只准备本次候选 boot `4126a297…bbfcf` 的正常启动转换。默认入口 `python3 -B check-local.py` 只做本地语法/已冻结字节检查，不导入 worker、transport 或设备代码，不创建文件。`prepare.py` 仅在本叶目录生成两份 worker/patch。没有 SSH、fastboot、刷写、部署或自动重启入口。

`prepare-contract.json` 是交给 root launcher / 独立 host operator 的实际字段接口；它不是现场收据。新 `samurai-eud-boot-activation-v1` schema、新 `eud-boot-*` transaction 和 token 同时绑定 quiesce/state/summary 与唯一 restart claim，旧 R7 stage、旧 R6 loaded-note、旧 440 及任何已有状态目录均不能复用。guard 与精确相机481 wrapper 放在新 `/root/charging-management-20261023/<transaction>/`，root-owned 0600，目录0700；个体 serial 摘要仅在 fresh 私有 guard，不进入公开例子。

每份 worker 都执行同一真实 guard：fresh旧boot guard、SoC serial原始bytes/compatible、精确uname/rootfs、taint0；实际 boot 分区96MiB hash必须仍为完整 a30 回退；logdump64MiB必须为 `aca01bc2…de8da`。这个完整 FAT 分区 hash 通过已有 `reference/kernel365/prepare-deployment.py` 的 `mcopy ::/Image` 验证绑定 Image363 `15746aab…d6468`，没有另造FAT解析器或把uname当Image摘要。两分区都只以 O_RDONLY 读取，实际BLKGETSIZE64核长度，关闭fd。

当前R8 manifest精确 `320316c3…c10a1f`，所有其安装文件及三provider的live/build-note都核对，与磁盘同版；不卸载/热替换 native provider。相机正式 wrapper精确 `1c458491…f4705`（r33/r28、新441三个模块、468 sensor和四原厂profile），逐项核安装文件/包版本/三个note，另核468 sensor实际note；不锁旧服务PID。新鲜完整充电样本必须无IO/保护/旧fault/timeout等，允许健康受控INHIBIT；source不明或错误不会因重启而被擦成通过。helper必须absent，MaxPower保持100。

quiesce直接复用已实际R7采用的 `normal-restart-candidate/r7-quiesce-review.py`；删除新guard、归一work/token收据字段后，硬件suffix逐字一致。它显式 `samurai-charging stop`，再沿原服务/音频/相机资源/DSP/DRM停机顺序，保留相机provider。失败目录留存，不自动重跑或声称已恢复。

restart复用原已测 `transport-tail-audit/r7-restart-transport-tail-review.py`（f7cfc985…dc615）。inspect在 `/dev/mem` R/W open之前退出。commit只接受CSR完整word **0、1、0x01010101**，不按低byte泛化；独占claim file及父目录fsync后才freeze、unbind EUD、写完整0并要求完整0读回，随后立即一次RESTART2("bootloader")。关闭EUD后的日志/JSON/SSH错误不能拦截syscall。syscall返回仍thaw并报错，不自动接回EUD/重试。最终phase只记录armed意图；SSH断开不是执行成功证明。root须用单次detached Popen和已核tmpfs `/run` 独立日志，未知结果沿同PID查，不重放。

本次仅运行18个实际guard接受/拒绝案例和7个实际restart try体的全字CSR/claim案例（fake OS/MMIO/syscall）。覆盖R8+481接受、受控INHIBIT、旧schema/transaction/boot/token/SoC、候选/分区/实际boot/logdump、R6note/旧相机/468note/旧440、timeout/stale/旧claim，以及精确CSR三值、其它低byte1拒绝、低byte0但全字非0读回拒绝、claim竞争与fsync失败。测试不宣称SHA算法、真实MMIO或重启通过。旧17 guard与8 transport-tail案例只引用原收据，未重跑；原硬件quiesce序列未重测。

host flash与现场动作另由root/UI独立实现：本次只允许写这份候选或完整 a30 回退到boot，必须fresh唯一精确serial/msmnile/96MiB、每个动作独占claim，任何前序mutator存活/未知均禁止后续写。Image363/logdump/rootfs/相机/NV不在写路径。相机481归还proof是来源证据，不替代root的实际独占窗口。尚未执行本叶worker，也未准备/刷写/重启手机；实际新boot、panel、CSR0/EUD路由/枚举、USB500/APSD均未据此验收。
