# USB 远程唤醒结论（2026-11-11）

## 结论

本板当前**没有可用的 USB/VBUS 唤醒源**，不能声称 USB wake 已适配。

- PM8150 GPIO10 的 `extcon-usb-gpio` 方案被真机证据否定，已从板级
  DTB、udev 规则和包里删除。
- keep-connect RFC 在“控制器以为还连着、实际已拔线”时会布防
  `dp_hs_phy_irq`，导致每次 suspend 在 0.6 秒内被伪唤醒；插线事件
  resume 还曾让 Windows 报 Code 43。板级 `snps,gadget-keep-connect-sys-sleep`
  已关闭。
- 现在使用标准 DWC3 gadget suspend/resume。插着线和拔线两种场景都能
  正常 suspend，boot ID 不变。
- 真正的 USB/VBUS 唤醒应走主线 PM8150B Type-C/TCPM + `usb-role-switch`
  的 attach/VBUS 事件，而不是再引入 GPIO10 extcon。该层尚未实现和验证。

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

- 每次 `rtcwake -m mem` 后约 0.6 秒就 `PM: suspend exit`；
- `suspend.success` 每次 +1，但实际没有睡；
- `dp_hs_phy_irq` 每次 +1，说明是 PDC DP 唤醒 IRQ 把系统拉醒。

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

- PM8150B Type-C/TCPM attach/VBUS 唤醒：需要启用
  `qcom,pm8150b-typec`、标准 `usb-c-connector` 和 `usb-role-switch`
  图，并验证 `vbus-change`/`attach-detach` IRQ 能进入 PDC 唤醒路径。
- 同线 U3 host-resume：Windows NCM 保持 U0 时没有成功样本；在标准
  Type-C 层落地前不应再启用 keep-connect。
- 长期 suspend/功耗和 USB 重新枚举稳定性。
