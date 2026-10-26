# 修后 036 版本的两对象编译补充

本补充关闭原 [build-result.json](../build-result.json) 的“原卷缺失、最终源码尚未编译”缺项，不改原候选、patch、测试或旧收据。当前冻结候选 delivery 仍为 `0c377f57…808a`，控制源仍为 `036ea6c6…4ed27`。

根会话明确授权后，使用 Ubuntu/root、原 `reference/kernel284/storage.py::mounted_build()`，先核原 helper SHA `5cddb34d…7d42c` 与固定普通 32GiB backing `E:/edk2-samurai-out/kernel282/full-kernel-build282.ext4`，正常恢复原卷。没有修改 helper/lock/sysctl，没有 format、卸载、新 anchor 或长期进程。

只在新的私有 `post-power-gate-build/{source-view,kbuild}` 执行原 W=1 命令与 `modules_prepare`、两个指定对象。三个 phase 均返回0，零编译诊断；共享 qcom 源文件、头、Makefile、`.config`、`Module.symvers` 前后哈希相同。没有链接 module/Image，没有设备、SSH、USB、SDK 或 Git 操作，没有重跑原 7 组测试。

| 最终实际对象 | SHA-256 |
| --- | --- |
| `qcom_pmic_typec_5v.o` | `a77a59be0aec4240873725cf83db451241c68a4f1dffe5e86c24734d2c38e03e` |
| `qcom_pmic_typec.o` | `29d777347d9f689d515d235aeaa34aea6cde921d3252c5e3d763cf4148d76f21` |

[build-result-initial-strict.json](build-result-initial-strict.json) 完整保留最初 `passed:false` 原件：编译全通过，但脚本把全部 `# CONFIG_… is not set` 注释集也作为相同条件，因此失败。随后只读核对 private `.config.old`：其 SHA 与编译前共享 `.config` 完全相同，准确绑定原输入，不需要为文本比较再次恢复卷。唯一变化是私有 Kconfig 补了一行 `# CONFIG_VIDEO_QCOM_CAMSS_ICP is not set`；全部定义/启用/取值配置相同，共享配置未写。见 [configuration-audit.json](configuration-audit.json)。[build-result.json](build-result.json) 以这项明确审计补正总编译判据，未重编，也未隐藏首次结果。

**编译成功不代表本候选可接入。** UI 独审发现并经作者确认一个未来 API 生命周期缺口：quiesce 锁内复制 client、锁外调用 `cancel_join(context)` 的期间，另线程可 release 并销毁 context，造成回调使用失效 context 的可能。当前没有消费者/实机触发，但这是 036 候选的接入阻项。未用未声明的调用方约束掩盖它，也未擅改冻结源码。已报根，待另起最小修订提供真实 context pin/get/put 并覆盖该竞争；本补充只证明最终 036 对象能编译。

没有部署、充电/5V/PD/图标或物理验收结论。原候选的其它 route/physical epoch/新一致 Image/实物 gate 继续保留。
