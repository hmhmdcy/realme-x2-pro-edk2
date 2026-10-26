# EUD boot-only fastboot 操作者：离线候选

默认 `python3 -B fastboot-operator.py` 等同 `check-local`。它只读本地固定文件，不启动子进程、不访问USB、不建事务目录。当前只完成离线检查和 fake OS/命令边界测试，尚未调用 fastboot，也未刷写或重启。

输入固定为实际封装通过的候选 `4126a297…bbfcf` 和原 a30 回退 `a30fb444…ec280`，各100663296 bytes；每个动作都会核两个完整文件hash/长度、私有实封装receipt `6dafe9e1…87b44`、12命令rc0、原封装source、rollback inspection、激活contract与restart worker。serial只读私有 `kernel109/fastboot-identity.json`，公开工具与收据没有实际serial。Windows fastboot的路径固定，执行时记录其本地文件hash；未将新版本tool hash冒充已经设备验收。

根会话审核并独占设备窗口后，使用 session 的激活launcher导出**全新**事务目录内 `host-context-private.json`。该文件用 `samurai-eud-fastboot-context-v1` schema，绑定原guard hash、transaction_id/token/old_boot_id及七个同目录raw文件的 `{path,sha256}`：`guard`、`quiesce_state`、`quiesce_summary`、`quiesce_boot_id`、`quiesce_process`、`restart_dispatch`、`restart_claim`。具体字段校验在 `validate_context`；已和激活launcher作者逐项对齐，不能使用旧R7 stage、旧taint512或历史事务替代。

quiesce必须terminal/exit0、summary taint0，同一事务/旧boot/token，原PID/startticks/精确远端argv且实际absent或zombie。restart必须绑定原host durable claim、精确 `0fb0948b…6ddf` worker、单次dispatch及原SSH进程真实终态。SSH 0/255、捕获的 `filesystem_frozen_restart2_armed` 都只是传输终态或意图；不要求重启后还能取回消失的 `/run` phase，也不把它称为syscall成功。每次USB动作仍需重新核唯一精确serial、product `msmnile`、boot分区96MiB。

以下是WSL中的**分开动作**，`CTX`由根设为本次新私有context绝对路径。默认检查本身不需要任何现场动作。

```sh
python3 -B fastboot-operator.py check-local
python3 -B fastboot-operator.py check-local --context "$CTX"
python3 -B fastboot-operator.py inspect --context "$CTX" --execute --window-confirmed
python3 -B fastboot-operator.py flash-candidate --context "$CTX" --execute --window-confirmed
python3 -B fastboot-operator.py fetch --context "$CTX"
```

`rollback-original` 与 `reboot` 也各自需要显式 `--execute --window-confirmed`，不会由其它动作调用。rollback只写原a30到boot；reboot要求本事务最后一个显式image动作已成功。所有动作各只能claim一次。没有erase、fastboot boot、其它分区、自动rollback/reboot/retry，也没有SSH或启动脚本安装入口。

每个动作在同私有事务下建立 `fastboot-operator/<action>/`。先durable独占request，再启动同脚本detached owner；owner记录自身及每个真实Popen的PID/startticks、实际观察argv与精确requested argv，原stdout/stderr分别私有留存，真实wait returncode和raw hash独立留存。Popen后的metadata失败仍等待同一个child；丢失terminal收据、部分claim、未知child一律禁止新动作。一个命令完成太快而未取得startticks会拒绝通过，仍保留其直接wait终态。

CLI最多等20秒（`--wait-seconds 0..60`），超过只返回pending/unknown，owner继续等待同child；不kill、不重放。`fetch`只读原PID/startticks/argv比对和既有收据，绝不再调用fastboot。仅child消失而没有真实wait终态不等于成功。worker所有命令终态落盘后才开放下一个独立动作；已失败但终态确知的flash允许另行申请rollback。工具没有删除claim或强行清unknown的出口。

flash通过只表示本次boot写命令return0且原输出明确 `Writing 'boot' OKAY`；reboot return0也不表示新boot已经启动。新UUID/原key/R8与camera健康、完整boot分区读回、panel/console/CSR/EUD以及USB预算属于根会话后续独立验收，本工具不会代报。

`test-boundaries.py` 仅执行本工具真实校验/claim/dispatch/command函数，Popen及命令边界始终fake；测试使用临时目录与虚构identity，不调用exe。没有重复原boot封装/guard矩阵或现场测试。最初本地检查发现脚本名 `operator.py` 会遮蔽Python标准库，已改为 `fastboot-operator.py`；未发生任何设备动作。
