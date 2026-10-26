# 完整 TCPM 接管 APSD/QC：单向交接子部件，未完成共存

本目录已实现并离线验证真正的控制权撤销、寄存器隔离和完整 TCPM 启动接线。它不再通过 PD5V provider 把 PD 永久关闭；成功后仍由标准 TCPM 使用板级 sink PDO 协商，包括后续由板级配置允许的 9V。**本轮没有实现同一启动中的新物理连接周期重新授予 APSD，不能作为完整共存方案交付或部署。** 手机 506 的真实计时观察没有受到访问或操作。

`handoff.patch` 和 `source.json` 给出 8 个实际源码文件及其原件 SHA256。以 `tcpm-usb-budget-candidate` 的 `tcpm.c`/`qcom_pmic_typec_port.c` 为完整 TCPM 预算基线，Qcom 其余源自 `tcpm-sink-shutdown-candidate`，DWC owner 源自 `eud-route-pm-candidate`。原生 USB input 与 `apsd-final-transfer-candidate` 的最终总线 API/inc 不改；没有再改现已正确的 ONLINE 解码。

## 实际路径

1. Samurai 的完整 PD profile 在 `qcom_pmic_typec_probe()` 中强制调用 `qcom_pmic_typec_apsd_prepare()`，位置在 **`tcpm_register_port()` 之前**。不需要另加默认无人使用的 DT 开关。现有固定 5V/500mA 试验 profile 与其他板保持原流程；完整 PD 必须更换其板级 PDO，不能继续被精确固定 profile 判定命中。
2. `samurai_apsd_tcpm_quiesce()` 根据实际 Type-C device、共享 PMIC parent/regmap 和现有 DWC `samurai,apsd-typec` phandle 核对绑定。它持有真实 device 引用，先发布 `tcpm_fenced`，再用原 `owner_join()` 同步等待原 APSD worker 及窗口恢复。没有伪造 lease/capability token。
3. owner worker 的每次取消验证及排队都检查同一个持久 fence。已经进入最终一次 transfer 的 worker 必须先结束；之后的 owner/backend 绑定、普通 USB 软件重连及 resume 不能绕过 fence。owner 不存在时同样先保留 fence，以覆盖后绑定。
4. 当前初版接管条件是两次相隔 20ms、全部四个物理存在位为 off、Type-C vSafe0V=1 且 vSafe5V=0 的实际读数；每组状态读取限时 250ms。每次窄掩码写前后重读相同 off 状态。20ms 是本候选工程去抖参数，不声称来自原厂。所有读数仍存在物理变化的不可消除时间窗口，不把串行 regmap 读写声称为与真实拔插原子同步。
5. 仅清 `0x1362` 的 `0x6c`（APSD_EN bit3 与 HVDCP AUTH/AUTONOMOUS/ENABLE mask0x64），再清 `0x1358` bit7（APSD_START_ON_CC），逐项读回确认。其余位保持；不写 PD 四控、不强制 APSD rerun、不请求 QC 电压，不写内部 PMIC 电池充电配置、MP2650 参数、保护 FET、OTP 或 NV。
6. `pdphy_start()` 在开供电、启用 PD PHY/frame filter 之前只读验证隔离；`set_pd_rx(true)` 与所有 `pd_transmit()` 在进入 PHY spinlock/发送操作前再次只读验证。这个更早的启动边界覆盖了首次 RX 回调之前 PD 硬件已被 `pdphy_start()` 启用的情况。RX-off/hard reset/合同暂失均不向 APSD 交还权限。
7. 验证读错、隔离位意外重开等错误会锁存，RX/TX 守门不会自动修复寄存器。Type-C 的实际 devres 在 probe 失败/解绑收尾后释放 device 引用；硬件隔离与软件 fence 均不回滚。无 owner 配置时返回 `-EOPNOTSUPP`，完整 PD 拒绝启动。

锁关系：第一次 join 发生于 TCPM port 创建前，此时不持通知锁、port/input/PHY/route 锁，也不持新 helper 的 mutex。原 worker 不拿 `owner_registry`；原最终 transfer 仍可取得 input 锁并退出。运行期 verify 只读取 PMIC regmap 和 helper mutex，不调用原生 power_supply getter、TCPM getter、owner join 或 owner registry，因此没有 native→TCPM→native 的新互锁环。

## 离线证据

`test-result.json`：生产 helper 原源码执行 **105 条断言**，覆盖 **28 个实际总线调用失败点**、四个物理 off 条件、vSafe0V/vSafe5V、状态变化、过期读数、窄掩码保持、devres 错误释放及运行期故障锁存；真实提取的 5 个 owner 函数通过 **21 条断言**及持 input 锁 worker 的实际 pthread join；另有 **10 项实际调用点/顺序检查**。两组 C 测试均在 ASan/UBSan 下通过，编译器零诊断。这些是软件和并发证据，不是硬件 PD/QC 证据。

`build-result.json`：只在 `/home/cy122/charging-management-20261023/tcpm-apsd-handoff-objects-02` 的独立 overlay/private mount namespace 编译 6 个受影响 ARM64 对象，`W=1` 零 warning/error；`nm` 确认 probe→prepare、PHY→verify、helper→owner quiesce/release 的实际符号引用和定义。因 `struct pmic_typec` 增加字段，同时重编 port 与 PD stub，避免沿用旧布局对象。首次 01 编译也成功，但后置 nm 检查误把去掉前导空格的 `U symbol` 当作缺失；修复检查后 02 通过，原失败记录保留于 `build-first-attempt-result.json`，不冒充最初检查成功。

编译前核余量约 WSL 768GiB、E 142GiB；所有原 lower 输入及父挂载不变；完整 Image、`.config`、`vmlinux.symvers`、builtin 元数据、initramfs、gauge 对象逐字保持。没有完整 Image 链接、DTB 打包、手机访问、SSH、刷写、重启、USB 操作或部署。

重跑：在 WSL 执行本目录 `prepare-source.py`、`test.py`。`build-objects.py` 将已经存在的 02 视为不可覆盖输出，再次构建应先改成全新的私有目录并保留已有结果。

## 剩余边界

- **接管入口条件尚不完整。** off/vSafe0V 只是本轮暂用条件，不能从旧 PD5V 实现推导成完整 PD 的永久要求；USB-A 常驻 5V 供电即使 CC 开路也不一定出现 vSafe0V。下一步必须复用另一候选的实际 PM8150B ADC VBUS 通道，并将真实 5V、既有 PD 四控零和角色/状态联合用于已连接启动的继承源判定。当前已连接源返回错误，且没有自动 probe 重试；本目录不要求用户人工拔插。
- **动态归还 APSD 尚未实现。** 还要在真实物理 detach 后建立新周期，在 PD PHY/TCPM 已退出旧协议活动并可靠证明无合同后重新开放 BC1.2；新 borrower 必须具备实际托管引用和撤销/等待生命周期。现有 PD5V lease 仍是旧固定 profile 专用，绝不能拿来冒充完整 TCPM 周期中的许可。保持 fence 只是一阶段安全撤销，永久关闭 APSD 不是最终设计。
- **完整 PD shutdown 待合并。** 本补丁不修改另一代理负责的 9V→5V/ADC/关闭交接目录；本目录 Qcom .shutdown 保留原基线，完整 PD 不能在未合并那条真实路径前部署。合并时应按 `handoff.patch` 的函数级改动处理两个候选共同的 Qcom 文件，不能整文件覆盖另一候选。
- **板级与实际验证仍缺。** 还需真实 full-PD sink PDO/供应引用/PM 配置与 ADC 绑定、重新上电后的隔离保留验证、物理 detach/attach/唤醒、QC 非并发、失败收尾及实际 PD 报文。2026 SMB5 v4 作者补丁只作参考；根会话提供的 2026-10-19 维护者回复明确仍需要线上 TCPM 日志，dock/角色切换不构成 PD 证明。必须取得真实 Request/Accept/PS_RDY 及合同电压/电流，不能用本离线测试证明 PD 协商或 QC 成功。
