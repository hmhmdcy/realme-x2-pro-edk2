# SDP 输入上限提升到 900 mA

2026-11-03。目标不是伪造 DCP/CDP，也不是绕过 Type-C/PD 协商，而是让
**已经确认的 USB 数据端口（SDP）** 在板级输入能力范围内使用 USB 3.x
标准下行端口允许的 900 mA，从而避免 1280×720/30fps 相机取景时净放电。

## 结论与已测结果

当前电脑端口被 BC1.2 识别为 SDP，provider 仍报告 500 mA：

```
/sys/class/power_supply/samurai-usb-input/current_max = 500000
/sys/class/power_supply/samurai-usb-input/usb_type    = Unknown [SDP] DCP CDP C
```

新模块只在 `POWER_SUPPLY_PROP_USB_TYPE == POWER_SUPPLY_USB_TYPE_SDP` 时把
策略输入预算提升到 `sdp_boost_ua`（默认 900000 µA）。DCP、CDP、PD、
Type-C 和未知来源仍使用原预算。

实机（7.3.0-rc6-rmx1931-samurai-k363+，相机 1920×1080 源、
1280×720/30fps 显示）：

```
input_current_limit = 900000
constant_charge_current = 500000
telemetry: budget_ua=500000 sdp=1 boost_ua=900000
battery current: +30 .. +51 mA during 24 s preview
idle with same cable: about +350 mA
```

相机预览截图确认后摄主摄、1280×720、30 fps 正常显示。测试期间未出现
USB 断开、reset 或 over-current 日志。以上是本机/本端口实测，不表示
任何只有 500 mA 能力的 USB 2.0 端口都能提供 900 mA。

## 代码改动

`mp2650-core.h`

- `struct sm_sample` 增加 `sdp` 与 `sdp_boost_ua`。
- `sm_source_budget_ua()` 只在 SDP 且 boost 大于原预算时替换预算。
- `sm_policy_with_band_reason()` 仍取
  `min(source_budget, input_cap, SM_OEM_INPUT_MAX_UA)`，温度、电芯过压、
  Full、故障、超时保护不变。

`samurai-mp2650.c`

- 新增 `sdp_boost_ua` 模块参数，默认 `900000`，权限 `0644`。
- `sm_collect()` 读取 `POWER_SUPPLY_PROP_USB_TYPE`，使用精确枚举比较
  `usb_type == POWER_SUPPLY_USB_TYPE_SDP`；这里不是位掩码，不能用 `&`。
- telemetry 增加 `sdp` 和 `boost_ua`，便于现场确认策略来源。

运行时可立即关闭，无需重载：

```sh
echo 0 > /sys/module/samurai_mp2650/parameters/sdp_boost_ua
```

## 验证

离线策略测试：

```sh
gcc -std=c99 -Wall -Wextra -Werror -O2 -o /tmp/test-sdp test-sdp.c
/tmp/test-sdp
```

结果：

```json
{"sdp_budget_cases":8,"existing_safety_cases":5,"passed":true}
```

覆盖：

- SDP 500 mA 预算 + 900 mA boost -> 900 mA；
- 非 SDP 不受 boost 影响；
- boost=0 时不改变原预算；
- boost 低于原预算时不降额；
- Type-C/输入 cap 和 `SM_OEM_INPUT_MAX_UA` 仍能封顶；
- 未知预算不会被猜成 900 mA；
- 温度、电芯过压、TCA/Full 停止仍优先。

ARM64 模块构建：

```sh
make -C final-source-view O=final-build M=sdp-boost-build \
  ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j2 W=1 modules
```

结果：W=1 零新增 warning；vermagic 为
`7.3.0-rc6-rmx1931-samurai-k363+ SMP preempt mod_unload aarch64`。

产物：

```
samurai-mp2650.ko
SHA256 afb63dcbbaefae32de64b0d35a1bc9232facb0e2f2f07e7193109c0a23df5784
```

安装前后对比 `.text`：仅 `sm_collect`、`sm_telemetry_show`、
`sm_policy_with_band_reason` 及模块参数相关符号变化；没有新增导出接口。

## 安装与回退

安装时先停服务，备份原模块和 manifest，替换
`/lib/modules/$release/extra/samurai-charging/samurai-mp2650.ko`，
更新 manifest 中该模块的 SHA256，再启动服务。

服务同时加入 `boot` 和 `default` runlevel。本机实测
`samurai-radio` 可能在 `default` 里长时间停在 `starting`，导致后续
服务（包括充电）迟迟不启动；`boot` 中在 `samurai-usb` 之后启动
可以保证电脑 USB 调试期间先拿到充电策略。

本机备份：

```
/root/samurai-mp2650-before-sdpboost.ko
/root/manifest-before-sdpboost.json
```

回退：

```sh
rc-service samurai-charging stop
cp /root/samurai-mp2650-before-sdpboost.ko \
  /lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko
cp /root/manifest-before-sdpboost.json /usr/share/samurai-charging/manifest.json
rc-service samurai-charging start
```

## 边界

- 900 mA 是 USB 3.x 标准下行端口和本机 OEM 输入档位的上限；不是 PD
  合同、不是 DCP 识别，也不会提升 Type-C/PD 协商结果。
- 若主机实际只有 USB 2.0 的 500 mA 能力，900 mA 可能触发端口限流、
  掉压或断开。此时应写 `sdp_boost_ua=0`，或改用有源 Hub/充电器。
- 当前相机预览的净充入约 +13..+49 mA，余量不大；高亮度屏幕或额外负载
  仍可能抵消它。它是“不再净放电”的修复，不是高功率快充。
- 未验证所有主机、Hub、线材、冷启动和长期温升；不据此声称完整 USB
  供电或 PD 兼容性。
