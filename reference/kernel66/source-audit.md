# kernel66 来源审查与后续硬件顺序

2026-10-10。先用本机校验后的日志确定问题，再找相应驱动、绑定和板级资料。优先级：Linux 主线驱动/绑定 → postmarketOS SM8150 维护仓库 → realme 官方下游板级事实 → 社区补丁。跨机型代码须逐节点核对，不能整体替换 MTP 配置或电压表。

## 已采用

1. `CONFIG_INTERCONNECT_QCOM_OSM_L3=m` 在无模块的实际 initramfs 中缺少提供者。已有 DTS 包含 CPU interconnect 路径，改为内建后 policy0/4/7 出现，完整 CPU dmesg 的 SHA256 和 gzip CRC 通过。
2. `CONFIG_QCOM_SPMI_ADC5=m` 同样未加载。内建 ADC5 和它选择的 VADC_COMMON 后三路 PMIC thermal 和三个 IIO 设备出现；运行时摘要独立校验通过。

[SM8150 维护仓库的固定 6.14 配置](https://gitlab.com/sm8150-mainline/linux/-/raw/sm8150/6.14/arch/arm64/configs/sm8150.config) 也将这几个提供者内建。只采用匹配实际依赖的选项，未复制整份跨设备配置。[官方软件包](https://pkgs.postmarketos.org/package/main/postmarketos/aarch64/linux-postmarketos-qcom-sm8150) 指向 SM8150 内核；[旧仓库](https://gitlab.com/sm8150-mainline/linux) 声明迁往 `gitlab.postmarketos.org/soc/qualcomm-sm8150/linux`，新站访问受限，本轮未验证其最新 HEAD。

早期 `eud_setup()` 使用普通 ioremap 的堆栈来自校验通过的完整 dmesg。arm64 在 parse_early_param 前初始化 early_ioremap；[主线 early_ioremap API](https://raw.githubusercontent.com/torvalds/linux/master/include/asm-generic/early_ioremap.h) 和 [EFI earlycon](https://raw.githubusercontent.com/torvalds/linux/master/drivers/firmware/efi/earlycon.c) 支持成对 early_ioremap/early_iounmap。候选只改变一次性 CSR 映射，不调整 EUD 协议、reset、掩码或延时。运行验证状态见 session 66。

## 接下来需要的证据

| 顺序 | 实际异常/限制 | 下一步 |
|---|---|---|
| 1 | CPU7 2956800 kHz voltage/OPP 更新失败，初始频率 4294967295 kHz 被改为 2841600 | 实际主线 sm8150.dtsi 的 CPU7 OPP 止于 2841600000；qcom_cpufreq_update_opp 从 LUT 得频率后调整已有 OPP，失败将表项置为 CPUFREQ_ENTRY_INVALID（0xffffffff）。这是缺失 OPP 的明确线索；继续核对 SM8150AC 分档及相应 interconnect 带宽，先只读，不能凭其他 SoC 的同频节点补电压或带宽。 |
| 2 | a600000.usb 持续 deferred；QMP combo 缺 orientation/mode，aux bridge -ENODEV | 核对本机 Type-C/DP graph、提供者配置及 EUD 占用 PHY 的关系，保留 EUD，不做 USB/reset 干预。 |
| 3 | MTP 继承的 regulators-2/ldof2 在 cmd-db 不存在 | 它是 PM8009、ID=f，不是 PM8150L。先核对 stock 拓扑/实时 cmd-db，再决定是否删节点。 |
| 4 | 电量没有读数、充电未移植 | 主线已有 `ti,bq27541` 驱动，旧文档“主线无对应驱动”过宽；先确认该板 fuel gauge 型号、I2C 总线与地址。MP2650 充电参数不得按其他机型复制。 |
| 5 | 仅 firmware simpledrm/fb0 可用；native panel/touch/GPU 未验证 | 下游 19781 板级 panel/touch/电源拓扑是参考，先核对绑线、时序和主线绑定；不要把 simplefb 资源提示当成黑屏证据。 |
| 6 | UFS 已挂上全部 LUN，电源缺省提示 | 低于持续未工作的硬件；核对实际电源轨，不因启动早期 transient defer 就判 UFS 故障。 |

[realme 官方下游仓库](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source) 本地固定 commit `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6`，板号 19781。旧工程只取已核实的原始 Android 采集与该官方源码；不复用其错误移植实现。尚未找到并核实同机型完整主线移植，不能以其他 SM8150 手机仓库代替本机验证。
