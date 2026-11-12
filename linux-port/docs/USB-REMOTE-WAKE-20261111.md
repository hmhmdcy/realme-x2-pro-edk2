# USB 远程唤醒结论（2026-11-11）

## 结论

必须把两种唤醒分开：

- **插拔 USB 线/充电器唤醒**：PM8150B USBIN 最小观察器已在真机通过
  一次干净的 `s2idle` 插线测试，证明 SPMI child IRQ -> PDC 路径能
  唤醒 SoC。生产 PM8150B Type-C/TCPM 已接入，但 Type-C 端口的真实
  物理插线/拔线唤醒仍待执行。
- **同一根线已连接、由主机 USB resume 唤醒**：仍没有成功样本。当前
  DWC3 peripheral 路径在系统 suspend 时 soft-disconnect，Windows
  `UsbNcm` 又长期保持 U0；不能把插线唤醒说成 USB host-resume。

- PM8150 GPIO10 的 `extcon-usb-gpio` 方案被真机证据否定，已从板级
  DTB、udev 规则和包里删除。
- keep-connect RFC 在“控制器以为还连着、实际已拔线”时会布防
  `dp_hs_phy_irq`，观测到该 IRQ 增长；printk 局部时钟显示的 0.6 秒
  差不能单独证明实际未睡，但它不是可信唤醒源，且插线事件 resume
  还曾让 Windows 报 Code 43。板级
  `snps,gadget-keep-connect-sys-sleep` 已关闭。
- 现在使用标准 DWC3 gadget suspend/resume。插着线和拔线两种场景都能
  正常 suspend，boot ID 不变。
- 正式适配已走主线 PM8150B Type-C/TCPM + `usb-c-connector` sink；
  当前 gadget-only 数据路径不需要 `usb-role-switch`，也不重新引入
  GPIO10 extcon。USBIN 观察器只用于证明唤醒硬件路径，不是最终
  Type-C 设计。

## 2026-11-12 更新

标准 PM8150B Type-C/TCPM + `usb-c-connector` + PM8150B VBUS
regulator 已作为持久 DTB/Image 冷启动部署。Type-C `wakeup-source`
已使能，3 轮 15 秒和 1 轮 60 秒 `s2idle` 均睡满、boot ID 不变，
UDC/NCM 每轮自动恢复；Windows PnP Problem Code 0。

`typec-irq-probe/typec_wake_near.c` 在 suspend 边界生成真实 PM8150B
CC 事件后，系统在 15 秒 RTC 前 4–5 秒恢复，Type-C IRQ +4，TCPM
wake events 76 → 85；unarmed 和 `power/wakeup=disabled` 对照均睡满。
这证明 Type-C IRQ → SPMI → PDC 路径可用。随后 8 轮 15 秒
`s2idle` soak 8/8 睡满 17 秒，`suspend.success` 18 → 26，主机自行
重枚举，未触发强制 DWC3 重绑。诊断模块只是取证，已卸载。

但**物理插线/拔线唤醒仍未执行**，同线 U3 host-resume 仍未验证。
本文上面的 USBIN 观察器实验不能替代 Type-C attach/detach 验收。
当前部署、哈希和待执行的物理测试见
[`USB-TYPEC-WAKE-20261112.md`](USB-TYPEC-WAKE-20261112.md)。

## PM8150B USBIN 最小唤醒实验

2026-11-11 在现有 USBIN 观察器上完成一次真机验证。测试使用临时紧凑
DTB 和匹配内核的临时模块，不是生产 DTB：

```text
boot_id              b3db5a73-4a2e-4800-9273-863e4154e19d
suspend.success      3 -> 4
samurai-usb-input    0 -> 1
usbin-plugin IRQ     +1
wakeup event_count   2 -> 3
RTC wall elapsed     8 s（安全闹钟 60 s）
```

插线发生前 Wi-Fi SSH 已离线，证明系统确实进入 `s2idle`；手机在 RTC
到期前恢复，boot ID 不变。对照测试在无插线时睡满 22 秒，USBIN IRQ 和
online 均不变。测试后已恢复 UDC `soft_connect=connect` 并卸载观察器。

| 证据 | SHA-256 |
| --- | --- |
| 插线唤醒日志 | `058c4e28c781e5e6a738b92b06105a43788b4a4eca64db9cd6330554474a76c0` |
| 无插线对照日志 | `9118d305e1c1a0730e2307dc717f67001aa6d77e78317fb1572b7c752b3e28e1` |

日志位于
`E:\edk2-samurai-out\standard-arm64-v731\usb-pmic-wake-20261111\`。
该结果只覆盖“线未连接时插入”的 VBUS/USBIN 事件。屏幕是否点亮不是
判据；SoC 已被 `s2idle` 唤醒，但充电事件不保证 compositor 打开面板。

## GPIO10 证据

厂商参考 DTS `linux-port/refs/19781/sm8150-mtp.dtsi` 中：

```dts
extcon_usb1: extcon_usb1 {
    compatible = "linux,extcon-usb-gpio";
    //vbus-gpio = <&pm8150_gpios 10 GPIO_ACTIVE_HIGH>;
    ...
};

/*
&usb1 {
    extcon = <&extcon_usb1>;
    status = "ok";
};
*/
```

`vbus-gpio` 和 `&usb1` 消费者都被注释掉了；注释说明 GPIO10 改作马达
用途。我们之前的 overlay 只保留了 compatible，没有消费者，属于没有
硬件证据的板级约束。

真机采样（2026-11-11）：

- 充电时 `mp2650-input/online=1`，`extcon0/state` 仍是 `USB=0`；
- VBUS 拔插瞬间 `mp2650-input/online` 在 1/0 之间变化，
  PM8150 GPIO10 始终为低，`extcon-usb1` IRQ 120 计数始终为 0；
- `/sys/kernel/debug/gpio` 中 GPIO10 一直显示 `in low`。

因此 GPIO10 不跟随 VBUS，不能作为 VBUS 唤醒源。

## keep-connect 证据

在未插线、链路被误判为 U3 的状态下：

- 每次 `rtcwake -m mem` 后 printk 的 entry/exit 只差约 0.6 秒；本板
  s2idle 会冻结局部 printk 时钟，这个差值本身不能证明实际没有睡；
- 当次观测到的 `suspend.success` 增加和 `dp_hs_phy_irq` 计数增加，才是
  撤回 keep-connect 的主要风险证据；没有标准 Type-C attach/VBUS 源时
  仍不能重新启用该模式。

插线事件 resume 后，DWC3 跳过了控制器重新初始化，Windows 报
`Code 43 / request for USB device descriptor failed`。在手机上做
`dwc3-qcom` unbind/bind 后 UDC 恢复 `configured`，证明是控制器状态
没有重新初始化，不是主机驱动问题。

内核修复 `8b9a05b3c` 增加了“cable event 回退到完整 reinit”的分支；
但本板没有可信的 attach/VBUS 状态，继续启用 keep-connect 仍会产生伪
唤醒，因此板级提交 `2b9ef80ba` 关闭了 keep-connect。该回退代码保留，
供将来接入标准 Type-C 源后重新启用。

## 当前验证结果

设备启动后：

```text
/proc/device-tree/extcon-usb1              absent
usb@a600000/snps,gadget-keep-connect...    absent
usb@a600000/wakeup-source                  absent
UDC                                        configured
PDC dp/dm/ss IRQs                          present, count 0
```

插着线 suspend：

```text
rtcwake -m mem -s 20
RC=0
suspend.success: 0 -> 1
boot_id unchanged
UDC: configured -> default（标准 soft-disconnect，主机可重新枚举）
```

拔线后 suspend：

```text
rtcwake -m mem -s 30
EPOCH_END - EPOCH_START = 32 s
RC=0
suspend.success: 1 -> 2
dp_hs_phy_irq count unchanged (0)
boot_id unchanged
```

只读门禁：

```sh
linux-port/scripts/check-usb-suspend-baseline.sh
```

## 产物

目录：

```text
E:\edk2-samurai-out\standard-arm64-v731\usb-resume-fallback-20261111\
```

| 产物 | SHA-256 |
| --- | --- |
| `Image` | `1e9b4ca98548a1a5dc3576799845df03b125b0e5843e343c718d729d42e3fbd3` |
| `sm8150-samurai.dtb` | `5c957d06cae9a5ad6541f8e5707057337f8c100b33e9447837e8daa0274d8472` |
| boot | `4f62605fc11a3b9b3594e745c5667572c3224ef85eb048c894d5c9c521ee9835` |
| logdump FAT | `898e76086b4beaf654927b2084e8ecb09fab9541df06541c20e07e252a133979` |

刷入脚本：

```text
linux-port/scripts/flash-v731-usb-resume-fallback.ps1
```

## 回滚

上一版 boot/logdump（extcon + keep-connect）：

| 产物 | SHA-256 |
| --- | --- |
| boot | `a4627d1564deac7e7d659ddd510a3fab95c3caff8c9d2f50146b76f9b209908f` |
| logdump | `3c7d9ff4c0116f5dde5ae169e69f062b48a388c96f3916096cd82656f3cf13d1` |

回滚只写 boot/logdump，不触碰 NV、persist、calibration 或 userdata。

## 未完成

- PM8150B Type-C/TCPM 正式适配：`qcom,pm8150b-typec`、标准
  `usb-c-connector` 和 `vbus-change`/`attach-detach` IRQ 的 PDC
  唤醒路径已部署并通过 boundary 诊断；仍需物理插拔/反插验收。
  只有扩展到 dual-role/host 时才需要 `usb-role-switch` 图。
- 同线 U3 host-resume：Windows NCM 保持 U0 时没有成功样本；在标准
  Type-C 层落地前不应再启用 keep-connect。
- 长期 suspend/功耗和 USB 重新枚举稳定性。当前 Windows 主机在
  `usb0` up 时仍会周期性触发 USB reset/re-enumeration；`usb0` down
  时 20 秒内未复现，需继续区分 Windows `UsbNcm` 电源策略、网络流量
  和 DWC3/NCM 生命周期。
