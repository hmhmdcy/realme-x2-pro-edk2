# 481：真实安装、精确回退、再安装准备

仅离线准备，未绑定 fresh 授权、未访问设备/SDK，未执行包事务。最终未绑定物料为 `E:/edk2-samurai-out/kernel481/k481-package-adoption-r1-offline-template-r2/`：40文件，归档29,018,019B，SHA256 `b9524d904438527c0e632ed383ae7404ec7647520bc88fccbef9db95517aab80`。旧r1草稿保留且未部署；检查见 [preparation-validation.json](preparation-validation.json)。

复用475签名物料和440实际安装/service/pidfd/durable-state前缀。计划为原生APK精确7包 r33/r28 → r32/r27 → r33/r28，配套4模块/4 profile；每相位停PW/WP及已知客户端，证实无live相机FD、idle/owner0，再先卸CAMSS、m2m/core、sensor，原路径换文件并按sensor/core/m2m/CAMSS顺序加载。模块依赖/alias元数据相等，不扩依赖或重建Image。APK默认scripts/triggers/hooks开启；两套7包本身无scripts/triggers，实际全局hook清单由fresh备份记录，不声称未发生的hook验收。

切换前保存并fsync本轮真实文件、属性、world、完整repositories清单、服务及原DB forensic。DB恢复只通过原生APK，绝不raw覆盖；每相位核非七包DB entry不变、包文件/模块notes/profile/属性及原信任集。回退核原world/repo字节和完整成员集合，模块与profile从本轮新鲜备份恢复；失败整体保持false，即便恢复成功。未知live APK保留同PID/start-ticks句柄等待，不杀、不重放；无法证实安全恢复则终态failed/manual并留具体状态。

两次forward直接调用冻结的482回调（默认/usr路径、有效IPA签名及native分支、四摄640×480/RAW/dual），不复制另一套probe。成功才保留r33工作基线：原repo内容保持，仅新增 `61-samurai-camera-r33-k481.list` 和 `/var/lib/samurai/camera-r33-r28-k481-r1` 的8个签名物料（root:root，目录0755/文件0644）；world仅更新/追加七pins，其他内容保留，最后通过默认系统repositories的no-network simulate核持久lookup。原始备份仍在事务私有root。

worker启动后300秒停止向前；480秒只作诊断预算，超时记录overrun/失败，不跳过已授权且安全确定的逐步恢复。每次APK等待90秒、模块命令15秒；超时仍live的APK继续观察同句柄，不能承诺硬终止时间。正常预计100–180秒，主线协调约10分钟并持有设备独占直至实际终态和归还。

由主线取得 fresh `k476-control-delay-r3` handoff；总授权精确为 `[k476-control-delay-r3,k481-package-adoption-r1]`，scoped仅476r3，使用实际新charging/adoption快照。只在全部ready后本地绑定一次：

```text
wsl -d Ubuntu -u root -- python3 -B "/mnt/e/RealmeX2Pro edk2/reference/kernel481/prepare-runtime.py" --handoff HANDOFF --owner-return OWNER --scoped-owner-return SCOPED
```

生成独立 `k481-package-adoption-r1-bound`，不会覆盖未绑定模板。`preparation-private.json` 提供 `query_sha256`（stage/launch/observe/collect）、`archive_sha256`、`worker_sha256`、`plan_sha256`。主线严格host wrapper先核hash再传输：stage-query以payload tar二进制为stdin，其他query以源文本为stdin。stage/launch不可重放；observe可查无根目录/同worker和active-child，collect只在终态且无live owned进程后回收含原始备份的私有tar。主线另做一次外部正式状态/健康核，准备收据不等于实际安装或默认路径验收。
