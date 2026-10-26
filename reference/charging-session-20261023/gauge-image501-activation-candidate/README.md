# Image501 activation：离线候选，未执行

默认 `controller.py check-local` 仅读本地输入，不连接手机。新事务匹配 `image501-[a-z0-9-]{8,64}`，计划首个为 `image501-gauge-live-001`；私有host根为 `E:/edk2-samurai-out/charging-management-20261023/image501-activation/`。未创建任何实际prepare/quiesce/restart事务。

当前身份取自已通过的4126新boot R3原件、实际新endpoint/adoption、Image363 latency500基线和normal-startup500原件；不用旧相机handoff的boot。执行时仍在原严格密钥/唯一endpoint上新鲜只读核对旧boot guard、SoC、uname、rootfs、完整boot4126/ACA分区、R8磁盘与loaded-note、相机481正式文件、startup SHA/MaxPower500及保护样本。固定内容和SHA见 `prepare-contract.json` / `input-pins.json`。这些私有原件是来源绑定，不能替代root实际独占交接。

候选成对绑定boot `97811cc4…67f695` / logdump `7e5de5b4…76cbf9`，精确回退为boot `4126a297…3bbfcf` / ACA logdump `aca01bc2…3de8da`；分别96MiB/64MiB。`partitions=['boot','logdump']`。此工具不刷分区、不卸native provider、不启动USB配置、不安装Phosh或修改rootfs/相机。两分区写入与后续reboot由root独立pair operator负责，禁止混合/未知组合启动。

硬件quiesce后缀相对旧已用版本，仅work标签变化，逐字相同。当前EUD-off不复用旧退役硬件body：新restart无 `/dev/mem`、mmap、CSR读写或unbind；仅只读确认native COM节点disabled、未绑定、无ttyEUD/console/bootarg，然后执行原durable exclusive claim、根文件系统冻结和单次RESTART2 bootloader。日志/SSH信息写失败不会拦已提交尾部；syscall返回或报错时解冻并关闭fd。Windows主机的EUD缺席不能由手机sysfs证明，需host另行新鲜核验。未声称重启、bootloader或物理恢复已经成功。

保留原Popen supervisor及同child真实终态、pending只fetch、original-terminal reconcile与未知不重发语义；remote仅改owner记录名和事务前缀。prepare上传新guard/两worker/481wrapper并只读验证；不停止服务。quiesce/restart每次持久intent，超时保留原进程/输出，不能按消失或SSH255冒称成功。partial prepare不清owner。inspect始终只读。

context为 `samurai-image501-fastboot-context-v1`，仍七份同目录basename+SHA raw：guard、quiesce state/summary/boot-id/process、restart dispatch/claim。内部dispatch/claim schema沿用原 `samurai-eud-restart-{dispatch,host-claim}-v1`；新guard/schema/tx/token与四分区hash绑定。export函数只改顶层schema literal，证据在 `context-scope.json`。armed记录仅证明一次意图；真实SSH终态和fresh fastboot身份仍需各自证据。

`test-delta.py` 只运行新4组：实际guard10例、实际无MMIO restart tail7例、quiesce/监督器/remote不变证明、实际host prepare单pending与旧事务拒绝。所有OS/transport/native syscall边界为fake；未执行远端worker。旧worker/host套件仅按原收据复用，未重跑。默认check-local已实际通过。新版#501/完整pair/param Y+cmdline/current_avg/startup500/native500的只读postboot采集器由root独立维护，不要求CSR或RAM ring采集。
