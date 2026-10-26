# 480：目标真实 APK providers，只读单次解算

主线实际目标验签及精确七包 simulate 已通过，设备已归还；未发生包事务。结果见 [HARDWARE.md](HARDWARE.md) 与 [runtime-validation.json](runtime-validation.json)。本地准备与离线审计代理未 SSH/SDK/设备访问。

准备阶段先生成完整未绑定工具，复用固定 hash 的477工具和475已签名 r33/r28 七包＋索引；480仅替换 namespace/stage 和预检 handoff 的476r2标识。保持 owner480秒、handoff600秒、boot guard/363版本及原信任集检查；不再做476控制测量。

主线取得总授权 `[k476-control-delay-r2,k480-target-deps-r1]`、scoped仅476r2及 fresh476r2 handoff 后，仅本地绑定一次：

```text
wsl -d Ubuntu -u root -- python3 -B "/mnt/e/RealmeX2Pro edk2/reference/kernel480/prepare-runtime.py" --handoff HANDOFF --owner-return OWNER --scoped-owner-return SCOPED
```

生成 `E:/edk2-samurai-out/kernel480/k480-target-deps-r1-bound/`。先审其计划/哈希，再使用既有严格原钥传输：`python3 -B -c STAGE_QUERY_SOURCE`，stdin为同目录 `payload-private.tar.gz` 二进制；其余 `launch-query.py`、`observe-query.py`、`collect-query.py` 用 `python3 -B -` 接收源文本。launch只一次；observe确认worker终态/不live后collect，collect stdout为私有tar。工具不自行传输，已有目标目录或一次标记拒绝重放。

目标仅运行 apk3.0.8 verify，成功后精确七包 `add --simulate --no-network`；私有 repositories/cache/tmp，禁scripts/hooks/global logfile，不修改依赖、keys、world或数据库。前后全局APK文件/目录清单与字节hash须相同；失败保留退出码与日志，不绕过。未绑定模板 `k480-target-deps-r1-offline-template` 在任何目标清单/写入前拒绝 stage/launch/worker。[preparation-validation.json](preparation-validation.json) 保留准备期快照及当时文件hash，不回写成已运行；后续README及新增审计文件属于运行收尾，字节与当时快照不同。
