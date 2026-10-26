# Image502：只读 USB / Battery / UPower 边沿采集模板

唯一来源是当前501采集器的最新SDP/CDP profile：launcher `4ae42851…0dec5`。只迁移#502、新logdump `ace2e261…763ed1`、不变boot `97811cc4…67f695`、本次`image502-notify-live-001`采用后的guard/endpoint/pins和独立输出目录。Image502 `085d0306…b25955`由完整ace2 FAT及其实际readback收据绑定。没有修改旧501叶、collector策略、桌面、UPower或系统policy。

worker、audit及原32例收据逐字相同；capture-entry只有guard常量变化。90秒稳定重接观察、300秒总deadline、130秒host ready余量、source/native/硬件输入/UDC/MaxPower/标准Battery NOW+AVG和净电流原件读取保持。SDP/CDP接受语义继承当前实际501 postboot profile，不在采集器里固定预算、不伪造Charging。FC/Full由真实Battery与遥测记录；本采集器不会强改。

当前只完成离线迁移、3组14个受影响实际函数fixture和两个默认检查，未联网、未启动采集、未生成真实identity pins。旧32/12及其它未变矩阵只引用收据，没有重跑。模板合成profile仅在临时目录验证，不能当真实#502 postboot/adoption。

## 直接使用顺序

1. root先完成实际#502 postboot和adoption。必须有新boot、完整boot97811/logdump ace2、R8/481/468/flagY/NOW+AVG及真实SDP/CDP通过的原件，现global pointer已采用本事务。新guard必须为`/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt`。
2. 本地只绑定实际原件，不联网：

```text
python3 -B bind-identity.py --adoption-directory /mnt/e/edk2-samurai-out/charging-management-20261023/image502-notify-activation/image502-notify-live-001/adoption-01-private --postboot-directory <本事务内实际passed的postboot目录> --execute-bind
python3 -B launcher.py check-local
```

`bind-identity`先写同目录next文件，实际reviewed_identity/adopt_local复核全部八份输入、原strict key及源码收据，再原子发布`icon-identity-pins-private.json`。缺passed postboot/adoption、旧501字段/guard/endpoint、混合载体均拒绝；未知next原件不自动删除或覆盖。无pins时默认check仍可通过源码，但launch拒绝。不要沿用旧采集事务。

3. 用户在旁且root已持有本轮独占窗口后，只launch一次全新事务：

```text
python3 -B launcher.py launch --transaction charging-icon-image502-001 --window-confirmed
python3 -B launcher.py status --transaction charging-icon-image502-001
```

等待status证实同一PID/start_ticks/argv、guard和manifest，连续两次fresh heartbeat递增、监视器活着且实际剩余时间不少于130秒，`may_prompt_user=true`后在3秒内发一次提示。未ready可继续只读status，不能再launch。可用提示为：“观察器已就绪，现在请拔下电脑端USB线约10秒，再接回同一口；接好后保持连接，继续观察。”

**五分钟是从launch起的总采集期限，不是提示后还能等五分钟才拔。** root应就绪后立即提示；人或网络耽搁需重新读取当前status，过期不能复用旧ready。没有增加一般权限审批；window指真实当前独占和现场条件。

4. 重接后保持观察，采集器需取得连续有效重接并再稳定观察90秒，或达到300秒总deadline。网络断开期间原worker在手机本地继续；传输未知只观察原事务，禁止另起worker、重播旧launch或以UDC configured替代物理source/ACOK证据。
5. 等原worker终态后只取同一事务：

```text
python3 -B launcher.py fetch --transaction charging-icon-image502-001
```

保留完整bundle/capture及所有失败输出，核`cleanup_confirmed`和原worker状态/terminal、dbus-monitor实际child终态与monitor errors。既有worker信号finally及持Popen的terminate/wait保持；本叶没有独立stopper入口，也不新增PID信号脚本。fetch不是停止动作，不能把收到某个旧status当原child已结束。

默认入口只做本地检查，实际已经rc0且`runtime_identity_available=false`：

```text
python3 -B launcher.py check-local
python3 -B bind-identity.py
```

主机新原件目录为`/mnt/e/edk2-samurai-out/charging-ui-audit-20261023/icon-capture-image502/<采集事务>/`；远端为`/root/charging-ui-audit-20261023/icon-capture-image502/<采集事务>`。原key/peer29/HostKeyAlias保持，不做IPv4/key fallback。报告应分别说明source/ACOK、Battery、DBus endpoint时间；原audit的first State估时不能扩大成目标State、屏幕像素或因果证明，也不能把离线通过称作实测延迟优化。
