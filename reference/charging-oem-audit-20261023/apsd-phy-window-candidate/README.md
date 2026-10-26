# Optional initialized femto-v2 PHY window

本目录是可选内部组件的离线实现，不安装消费者、不改当前 R8/USB provider、DWC/EUD 候选、共享源码、Image 或手机。输入来自 `../apsd-integration/current-r7/`：femto-v2 SHA `019dd4759be4955dfae6d92192c2fceb085a4e6945607e4942fb746cf2ab65a9` 已逐字关联原 Image 提交 `ba61a62293e0f6bc5838c06f2e85e033e3d702a8`。本地原Image关联与实际DTB说明沿用该目录 `image-source-linkage.json`，不拿新的 DTS 当当前部署树。

`phy-window.patch` 只改 `drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c` 并新增同目录内部头 `phy-qcom-snps-femto-v2-window.h`。当前固定配置为 `CONFIG_PHY_QCOM_USB_SNPS_FEMTO_V2=y`。API 未 `EXPORT_SYMBOL`，没有 UAPI/sysfs、regulator 节点、定时器或自动回调消费者；未来 owner 必须在同一 Image 内编译。当前常驻 `samurai-usb-input` 模块不能直接调用。

## 接口与所有权

```c
int qcom_snps_hsphy_window_begin(struct phy *phy,
        struct qcom_snps_hsphy_window_result *result);
int qcom_snps_hsphy_window_end(struct phy *phy, u64 cookie,
        struct qcom_snps_hsphy_window_result *result);
```

调用者在进程上下文串行持有一个 session/cookie，并保护真实 bound PHY/DWC 生命周期；调用任何组件时不持另一个组件的锁。普通 `get_device()` 不是防 unbind 的完整保护。owner 必须在 DWC/UDC/PHY stop/remove 之前 cancel/join 自身检测工作并恢复 PHY；不能等资源释放以后再拿旧 cookie 清理。

begin 仅接受本驱动 ops 身份、`phy_initialized=true`、generic `init_count>0`、USB_DEVICE 模式及已经 active 的 provider runtime PM。它在 generic `phy->mutex` 外调用 `pm_runtime_get_if_active(hsphy->dev)`，不调用任何 resume/init/reset/power/clock enable；inactive返回 `-EAGAIN`，PM错误透传。该独立 provider PM ref 在成功 claim 后保留至成功 end，失败不丢；重复 claim 所取的临时引用立即平衡。它用于保护本 PHY 的 runtime 生命周期，不能替代调用者的**成功 DWC active HALT window**，也不替代 EUD/PD/route 前提。

| 结果 | 调用者需要处理的状态 |
| --- | --- |
| begin=0 | cookie非零，state=HIGH_Z，三步 masked readback均通过，保留旧值和一个PM ref |
| begin<0，cookie=0 | 没有 claim、没有本次硬件写；其它 window 仍由原 owner 持有 |
| begin<0，cookie非零 | state=FAILED，可能已部分写，旧值/owner/ref保留；不可开展模拟检测，必须显式end恢复 |
| end=0 | 三组旧masked值已逐项恢复并读回，state=IDLE/restored=true；只释放本组件的PM ref，不连接DWC/EUD |
| end<0，合法cookie | state=FAILED，restore_error独立保留，owner/ref仍在，不能据此调用DWC/EUD end；由owner决定显式重试/安全故障策略 |
| end=-ESTALE | 无写入、无引用释放，不是恢复成功；包括空/旧/重复cookie |

`enter_error` 和 `restore_error` 独立；恢复成功仍保留之前进入错误作为历史。receipt 的 `attempted`、`verified`、`restored_mask` 按 entry 索引bit0..2记录，`saved[3]` 是原始 masked 位而非 hardcoded normal默认。`high_z=false` 的失败状态没有 high-Z 许可。这里的HIGH_Z表示已验证原厂指定的控制位状态，不能单靠数字读回证明物理D+/D−波形、EUD路由或PD inactive。

## 三组操作与恢复

精确复用本机原厂固定 `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6` 的 `drivers/usb/phy/phy-msm-snps-hs.c::msm_hsphy_dpdm_regulator_enable()`（缓存与完整函数在 `../apsd-lifecycle/`）。保留其三组顺序，不搬入原厂 enable 的 regulator/clock/reset 动作：

| entry索引 | PHY偏移 | mask | enter value |
| --- | ---: | ---: | ---: |
| 0 | `0x64` HS_PHY_CTRL2 | `0x0c` | `0x0c` |
| 1 | `0x3c` UTMI_CTRL0 | `0x18` | `0x08`（non-driving） |
| 2 | `0x94` CFG0 | `0x01` | `0x01`（datapath override） |

generic PHY mutex 内先读取保存全部三组旧masked位，再逐步 RMW并立即比较 masked读回；不动其它位。任何一步读回不符返回 `-EIO`，停止后续进入写入并保留owner，不自动回滚、更不自动接回 DWC。MMIO接口本身没有可透传的 I2C-style errno；检测到的是读回不匹配，不伪造“总线已正常”的结论。

end 在同 mutex 下按逆 entry 顺序2→1→0恢复**保存的旧位值**，每步比较读回。逆序是本候选的显式恢复策略，未冒称原厂 disable 已实现这套精确还原；原厂 disable 仅按 cable_connected 决定是否关电源/时钟。恢复失败可能已离开完整高阻，故 `high_z=false`，不重新宣称“仍然quiet”；保留旧值以供显式重试。RMW 保留结束时的非owned位，避免覆盖其它硬件状态变化。

## PHY生命周期串行

所有本组件 state/快照/generation 均受原 generic `phy->mutex` 保护，未引入第二把组件锁。generic `phy_init/exit/set_mode_ext` 已在该锁内调用 ops，新增 ops guard不重入 mutex：

- window拥有期间实际执行的 ops `.init/.exit/.set_mode` 返回 `-EBUSY`，不 reset、关时钟/电源或覆盖mode。generic `phy_init` 在 `init_count>0` 会跳过 `.init`，所以已有引用可1→2并正常返回；`phy_exit` 在count>1只2→1，亦可正常返回，不破坏快照。只有最终count=1、真正要调用 `.exit` 的退出被拒，且错误保留count=1；不能将其表述为generic init/exit一律拒绝。定向测试执行的就是实际generic流程。
- runtime suspend/resume callbacks也用同一 mutex，owned时返回 `-EBUSY`，不改变保存状态。进入前 active-only PM get 与正在进行的runtime转移不兼容就拒绝，不靠resume获取高阻。
- idle时原有init/reset、exit、电源时钟与mode行为保持；没有窗口时不新增任何masked写入。窗口 generation 跨普通exit/init保留，避免旧cookie误命中新借用。

默认路径的明确变化只有：增加零初始化的可选state；ops增加owned guard；runtime callbacks增加generic mutex和owned guard。probe的初始 `pm_runtime_get_noresume/set_active/enable` 与完成建立generic PHY/driverdata后才put的代码**原baseline已有且本patch未改**。它保证新增PM回调mutex使用 `hsphy->phy` 之前对象已建好，是本候选依赖的初始化前置；不是声称本轮另修了原厂PM策略。idle runtime回调现在与set_mode/exit串行，原本DEVICE无MMIO、HOST原auto-resume动作均保留。

system PM仍由整个session的DWC prepare/complete栅栏覆盖；provider引用本身不等于禁止系统sleep。普通remove可能释放整个对象，不能靠留下FAILED结构体保护已释放的MMIO，所以未来owner的bound lifetime/cancel/join是必须实现的调用契约。本候选不新增强制unbind或失效对象上的恢复行为。

## 和现有组件组合

已与DWC R2及EUD组件作者对齐：未来owner按EUD begin→DWC begin（成功HALT）→PHY begin串行调用；不跨组件持锁。只有PHY enter成功才可由独立PD/route/PMIC owner开展模拟检测。结束先停模拟动作→PHY end精确恢复成功→DWC end→EUD end。PHY失败时保留DWC/EUD quiet owner状态，不自动往后接回；DWC恢复失败同样不能无条件EUD end。

DWC end成功释放自己的PM ref，不释放PHY以外其它owner引用；整个PHY→DWC→EUD清理过程的电源/取消策略仍由session owner维持。若DWC已SHUTDOWN/解绑，不能把PHY token存在当作模拟资源仍可用；先执行owner取消与join。这个patch只实现所需组件，不假称完整一次APSD/PD/EUD事务已经完成。

## 验证与交付

`test-result.json`：8组，直接执行15个完整candidate/generic-PHY函数；函数行号/SHA在 `function-manifest.json`。ASan/UBSan和-Werror通过，涵盖三组写顺序、精确旧值/非owned位恢复、每个进入/恢复读回失败、独立错误、single owner/ref/旧token、真实generic exit/setmode/count拒绝、runtime回调、普通idle init/reset/exit、exit赢得claim前竞争。OS/PM/MMIO为桩，未做kernel lockdep或穷尽并发，也不是物理验收。没有重跑已有DWC/EUD/USB套件。

`build-result.json`：原配置的私有source-view/O目录，仅 `modules_prepare` 与 `drivers/phy/qualcomm/phy-qcom-snps-femto-v2.o` W=1通过、0 warning/error；共享源码/config摘要均不变。未调用SDK，未构建Image/package。`delivery.json` 绑定最终patch、实际测试和编译收据。

离线重现（各脚本只处理本目录和独立私有构建目录）：

```text
python3 make-candidate.py
python3 run-tests.py
python3 build-private.py
python3 seal-delivery.py
```

尚无部署或硬件采集动作；本目录没有设备执行命令。
