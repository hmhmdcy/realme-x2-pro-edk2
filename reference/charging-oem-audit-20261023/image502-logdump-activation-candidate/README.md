# Image502：只更新 logdump 的离线激活候选

本叶只写一个目标分区：logdump。候选是 `ace2e261…763ed1`，回退仅当前Image501的 `7e5de5b4…76cbf9`；boot `97811cc4…67f695` 是只读不变量，不存在flash boot路径，也不回退4126/ACA。普通修复与正常重启授权沿用，现场条件仅指根需核实有人可在历史fastboot不枚举时协助；没有新增审批或冷却。

当前只完成源码派生、5组22个受影响actual函数检查、纯本地materialize及两个默认check-local。未执行prepare、SSH、quiesce、restart、USB/fastboot、构建或部署。准备合同由真实通过的502/FAT收据生成，不把模板字符串或已结束501事务当有效新事务。

## 固定输入与合同

Image502 `085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955`，59243008B；作者delivery `4e27a8da…163e21`。FAT作者delivery `eb615331…420ce`、logdump-result `c08d9830…e6758`，实际64MiB候选 `ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1`。FAT内的A823 fallback DTB与当前boot嵌入9271不是同一件，本轮两者都不改。

`materialize.py` 先核作者冻结delivery、实际成功FAT原件、三个真实包装命令终态、只变Image/非Image字节保持/readback/fsck证据，再以1MiB分块hash核新旧64MiB FAT、Image502及96MiB原boot；不把大文件整块read_bytes。缺失、未passed、文件或哈希不一致时，在创建合同目录前拒绝。原FAT首次ENOMEM历史在作者叶保留，本叶没有把它改判为载荷失败或成功。

唯一已生成本地材料在：

`/mnt/e/edk2-samurai-out/charging-management-20261023/image502-notify-materialized-001/`

其中materialization SHA `09c4a086…2d4e`，prepare-contract `469d2aab…c60ba7d`，resolved quiesce `796868d4…b060`、restart `3e9c4036…085f`。合同明确 `partitions=['logdump']`、unchanged_boot97811、rollback7e5；resolved worker、合同、source、22例收据及所有物料逐项绑定。模板保留材料化标记，不能直接被当成已解析worker。operator只读同一materialized目录中的activation-pins，没有第二份漂移pins。

## 当前身份与一次事务

新事务只能为 `image502-notify-live-001`，新token和目录；主机原件在：

`/mnt/e/edk2-samurai-out/charging-management-20261023/image502-notify-activation/image502-notify-live-001/`

profile取实际Image501 adoption/postboot04/endpoint和原key的固定来源，要求同一新boot、精确#501 uname.version、rootfs/SoC/compatible、当前adopted guard、97811/7e5、R8 manifest320316、481/468、startup500与瞬时电流flag。旧#363/4126 guard不能通过。历史501 flash与reboot的同上下文真实terminal/commands_terminal成功证据，以及实际postboot/adoption，作为该旧事务已结束的来源；保留旧journal、不清unknown、不重发旧动作，不把另外改一个锁路径当绕过活owner的方式。

远端prepare会再读当前boot/板型/根FS/完整分区/R8/相机和EUD producer缺席。所有新动作仍受当前根独占窗口控制。只读安全采样严格区分启充正常/精确Full；成功quiesce之后restart/inspect只接受本事务同token/boot的成功quiesce原件，以及真实INHIBIT样本的一致状态，不错误要求已经主动停充的系统继续desired_enable=1。输入限额按实际source预算核对，SDP/CDP不混成固定100或500。

controller复用原durable once intent、同Popen PID/startticks/argv、真实wait与fetch/reconcile。未知/活着/缺终态时只观察原child，不能重发、kill、删目录或制造成功。实际quiesce硬件suffix与正常restart2 bootloader尾沿用501：停充/服务及原硬件收拢，fsync独占claim、sync/freeze、一次syscall；返回/错误则thaw。记录日志失败不能阻断已提交尾；SSH断开、armed或host child终态都不等于已进入bootloader。没有EUD CSR/MMIO/退役或运行期路由操作。

## 本地入口与未来执行顺序

默认均只检查本地字节，已经真实rc0：

```text
python3 -B controller.py
python3 -B fastboot-operator.py
```

将来由根核当前现场条件和独占交回后，使用本叶controller依次prepare→quiesce→fetch确认原worker终态→inspect-restart→restart；各操作使用固定新事务和既有 `--execute --window-confirmed` 参数语义，不代表再索取一般授权。export的host-context只包含本事务七份准确原件。不会要求新boot去找已消失的旧/run日志。

随后单独fresh fastboot唯一serial/msmnile和分区几何。operator `flash-candidate` 只flash logdump，成功写入与真实child终态后，另一次 `reboot-candidate` 才可发reboot。`rollback-original` 仅完整原7e5 logdump；它也不自动reboot。原件每次派发前重新核hash。未枚举则观察/现场协助，不重发restart；未知写动作阻止后续写或回退。boot分区尺寸查询不是其内容hash证明，97811内容由Linux前后完整只读hash及本叶零boot写范围绑定。

后续#502新boot、完整新logdump/旧boot、R8/相机/服务/保护、flagY/AVG和合法动态预算须由根独立只读收集。这些工具不把fastboot rc0称作实机启动、PM或图标时延验收。Phosh/UPower改动路线保持取消。

## 受影响验证

`test-result.json` 5组22例直接执行实际新profile、充电阶段判断、logdump-only run_action、reboot_binding/prior_terminal、同目录pinned_tools和失败materialize门；USB/transport边界fake。覆盖旧身份/旧ACA/旧unknown拒绝，正常/Full/绑定quiesce INHIBIT，候选与回退只有logdump写、混合双分区证明拒绝、缺terminal不能前进、pins漂移与未passed FAT零合同。28个未变控制/once/wait函数逐字绑定，旧4/6/7等矩阵收据复用，没有重跑。

生成器与材料化过程分离；材料化已完成后不要再次运行prepare-tools或改已绑定source。所有相关源与本地材料摘要由delivery绑定，物理原件留私有目录，不打包二进制或私有身份。
