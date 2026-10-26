# Fastboot操作者 R2：按镜像阶段各一次显式重启

旧 `eud-fastboot-operator/` 的 b8f043源码和17组收据全部保留。R2只修候选重启已消耗唯一 `reboot` claim 后，显式回退成功仍无法重启原a30的收尾缺口；没有执行fastboot或设备动作。

使用R2的 `fastboot-operator.py`，其它动作及七raw context接口不变。默认仍为只读本地 `check-local`。

```sh
python3 -B fastboot-operator.py check-local
python3 -B fastboot-operator.py inspect --context "$CTX" --execute --window-confirmed
python3 -B fastboot-operator.py flash-candidate --context "$CTX" --execute --window-confirmed
python3 -B fastboot-operator.py reboot-candidate --context "$CTX" --execute --window-confirmed
```

若候选未能启动，根在明确恢复fastboot且原命令终态确知后，另行决定以下两个**独立**动作；工具不会自动串接：

```sh
python3 -B fastboot-operator.py rollback-original --context "$CTX" --execute --window-confirmed
python3 -B fastboot-operator.py reboot-original --context "$CTX" --execute --window-confirmed
python3 -B fastboot-operator.py fetch --context "$CTX"
```

`reboot-candidate`只能对应最后一次image动作 `flash-candidate` 成功且SHA精确4126；`reboot-original`只能对应最后一次 `rollback-original` 成功且SHA精确a30。两者各自仅claim一次，即使重启命令失败也不重放同阶段。重启request还绑定对应image的原claim/result hash，worker在实际命令前复核。最后image失败/未知、其它pending动作或旧版 `reboot/` claim均阻止借新名字绕过；旧版已开始的runtime事务不能直接迁移为R2阶段。

原Popen同child wait、超时不kill/retry、唯一serial/msmnile/boot96MiB、全镜像hash、boot-only、未知状态阻断和context校验逻辑未变；`command`、`process_info`、`fetch`、`validate_context`、`local_inputs`、`main`函数源码逐字对比相等。原17组仅复用其冻结收据，本次未重跑。

本次仅执行 `test-reboot-phases.py` 的两条真实状态函数序列：候选成功刷写/显式重启→成功回退/单独显式重启；候选重启失败禁止同image重试→回退pending禁止跨阶段绕过→回退失败拒绝两种重启。命令边界始终fake，镜像只读核hash，不调用fastboot/USB/SSH/SDK/Git。它们不证明硬件启动成功。
