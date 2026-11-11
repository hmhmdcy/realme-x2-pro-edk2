# RMX1931 boot error triage (2026-11-10)

> **2026-11-11 后续**：本文引用的 PM8150 GPIO10 `extcon-usb1` 唤醒源
> 已被真机否定——厂商 DTS 注释掉 `vbus-gpio` 和 `&usb1` 消费者，实测
> GPIO10 不跟随 VBUS、IRQ 120 始终为 0。overlay/udev 已删除，
> keep-connect 也已关闭。当前结论见
> [USB-REMOTE-WAKE-20261111](USB-REMOTE-WAKE-20261111.md)。

Status: evidence collected; fixes are deferred to the next session.

This report separates the USB-wake DTB integration from unrelated userspace
and display failures observed in the same boot. The extcon/PDC wake source is
present, but no suspend/wake test has passed yet.

## Boot identity

| Item | Value |
| --- | --- |
| boot ID | `80c11929-3065-463f-a7b4-c98a905dcc61` |
| kernel | `7.3.1-rmx1931-samurai-v731` |
| taint | `0` |
| boot carrier | `62dee7b9a3c11a2bc549e570b57c35911fa8aa0b0220fe182dd7ec7dc4fab152` |
| rollback boot carrier | `5b4dd4871f6856710ff58e722ffd8b2c30d04baf0104b262adcb02e46a7651bf` |
| embedded DTB | `bf795923df7bcb0b864766e840bef1fede752c2c89c7822ee090c4bab6a55f6f` |
| runtime FDT | `f4486e0e293f71e2048f8607c3f1a3c36599e8eb514f19c7f417f48a9d803876` |
| kernel FAT Image | `f8d8962197827dafbe50e551f5df03391c43ec0269449fa87b833e57799656a5` |

The boot carrier passed the DTB-only metadata review: BDS,
PlatformSmbiosDxe and UiApp are byte-identical; only DTB FFS
`25462cda-221f-47df-ac1d-259cfaa4e326` changed.

## USB wake source: present

The DTB-only USB wake change is active:

```text
/proc/device-tree/extcon-usb1
compatible = linux,extcon-usb-gpio
power/wakeup = enabled
IRQ 120 = spmi-gpio, Edge, extcon-usb1
```

This proves DT parse, driver probe, wakeup capability and IRQ registration.
It does **not** prove that inserting or removing a cable wakes the system.
The suspend test remains mandatory.

## Primary blocker: kernel/module release mismatch

The running Image uses release
`7.3.1-rmx1931-samurai-v731`, but the rootfs only has:

```text
/lib/modules/7.3.1-rmx1931-samurai-v731+
```

`lsmod` is empty. This is the dominant cause of the boot-time failures:

| Symptom | Evidence | Consequence |
| --- | --- | --- |
| `socinfo` unavailable | `/sys/devices/soc0/serial_number` is absent | `samurai-usb` waits 60 seconds and fails; no UDC/NCM gadget |
| Bluetooth module rejected | `btbcm` vermagic says `7.3.0-rc6-...` should be `7.3.1-...v731` | `bluetooth` does not start |
| RTC module unavailable | `hwclock` cannot access any hardware clock | RTC fallback for suspend tests is currently unavailable |
| zram module unavailable | `postmarketos-zram-swap` fails | zram swap does not start |
| sensors/modules incomplete | `samurai-ssc` stops and `iio-sensor-proxy` becomes failed | KWin logs SensorProxy `NoReply` |

Do not treat these as USB-wake regressions. The same mismatch will also make
any USB suspend test unreliable because the RTC and gadget dependencies are
not fully available.

## Display failure after lock-screen swipe

The physical panel showed the lock screen and touch input worked. After the
swipe, KWin logged:

```text
kwin_wayland_drm: Atomic commit failed: EBUSY
kwin_wayland_drm: Atomic commit failed: EBUSY
```

At collection time the display state was still:

```text
DPMS=On
DSI status=connected
backlight brightness=1024
bl_power=0
```

Therefore this is currently a black physical panel after a failed atomic
commit, not necessarily a DPMS-off transition or a power-key failure.

The USB wake DTB changes only `/extcon-usb1`, the PM8150 GPIO10 pinctrl state
and the SPMI parent interrupt routing. It does not change DPU, DSI, panel or
PowerDevil behavior. This display failure must be debugged as a separate
DRM/KMS issue.

## Other service failures

| Service | Classification | Next action |
| --- | --- | --- |
| `samurai-usb` | blocked by missing matching `socinfo` | install matching modules, then retry UDC/NCM |
| `bluetooth` | blocked by wrong module release | install matching modules, then retry HCI |
| `postmarketos-zram-swap` | blocked by missing zram module | retry after module repair |
| `iio-sensor-proxy` | failed after `samurai-ssc` stopped | retry after modules; keep it non-blocking for display |
| `polkit` | service is stopped although the binary exists | start manually and capture stderr; do not disable blindly |
| `urfkill` | `urfkilld` is absent | compare against official pmaports and likely retire in favor of the standard `rfkill` service |
| `samurai-ssc` | private SLPI/SSC stack unavailable | preserve as an optional service; it must not gate the desktop |

## Non-fatal kernel noise

These messages are noisy but not first-order blockers:

- RPMh regulator `-95` errors while reading voltage/enable state; RPMh reads
  may simply be unsupported. Verify against the driver before changing DTS.
- `trace_boot: Failed to enable event: samurai_diag:*`; likely stale debug
  tracing configuration.
- SLIM NG device-link failures for the audio codec; audio routing already
  has a separate ownership layer.
- `regulatory.db` missing and ath10k random MAC fallback; Wi-Fi still
  associates, but MAC stability and regulatory data need separate cleanup.
- One AP rejection was observed (`status 33`), followed by a successful
  association. Do not classify this as a kernel wake failure.
- Plasma/QML/PipeWire/RTKit warnings are userspace integration noise. Fix
  only if they break a required user path.

## Next-session repair order

### 1. Restore a matching module tree first

Use the exact Image build tree
`/home/cy122/samurai-v731-build-archive-20261108`, generate and install a
stripped module set for release `7.3.1-rmx1931-samurai-v731`, and verify:

```sh
modinfo -F vermagic /lib/modules/7.3.1-rmx1931-samurai-v731/kernel/.../*.ko
lsmod
cat /sys/devices/soc0/serial_number
ls /sys/class/udc
cat /sys/class/rtc/rtc0/name
```

Do not install the existing `...+` module directory into the `...v731`
kernel.

### 2. Re-run the service gate without changing USB wake

After reboot with matching modules:

```sh
rc-service samurai-usb start
rc-service bluetooth start
rc-service postmarketos-zram-swap start
rc-service iio-sensor-proxy restart
rc-service polkit start
rc-service urfkill status
```

Capture stderr for `polkit` and `urfkill` before deciding whether the
service should be repaired or removed. A failed optional sensor service must
not block `tinydm`, KWin or the lock screen.

### 3. Validate cable-insert USB wake

Only after `rtc0`, UDC and NCM are restored:

1. keep the old boot carrier as rollback;
2. arm a bounded RTC wake as a safety net;
3. enter `rtcwake -m mem -s 120` with USB unplugged;
4. insert the cable before the RTC deadline;
5. require the same `boot_id`, a positive `suspend_stats/success` increment,
   and the extcon IRQ plus `power/wakeup=enabled` evidence;
6. repeat with cable removal, then positive/negative cable orientation.

An RTC-only wake is a failed USB-wake test.

### 4. Add same-cable USB host resume separately

The current DTB validates only VBUS insert/remove wake. Same-cable
host-initiated resume still needs a generic DWC3/QUSB2 peripheral wake path,
including DP/DM wake IRQ arming and avoiding unconditional gadget
soft-disconnect during system suspend. Do not mix that kernel layer with the
already verified extcon DTB.

### 5. Debug the `Atomic commit failed: EBUSY` display failure

Reproduce the lock-screen swipe while collecting:

- DPMS and backlight state before and after the swipe;
- `dmesg -w`;
- KWin/tinydm output;
- DPU/DSI atomic-commit and VBLANK/TE tracepoints;
- `/sys/kernel/debug/dri/1/state` and relevant DPU/DSC snapshots.

The key distinction is whether the failed commit is followed by a modeset,
an output disable, or only a stale black panel. Do not use
`kscreen-doctor --dpms on` as a permanent fix; it is only a diagnostic
workaround.

## Evidence

Collected archive:

```text
E:/edk2-samurai-out/standard-arm64-v731/usb-wake-deployed-20261110/samurai-boot-error-review.tar.gz
SHA-256 63f4485943d449fed1adc3bacbb8719f3f6e623fcbe144902ad8f5fed3c850bd
```

Extracted copies:

```text
E:/edk2-samurai-out/standard-arm64-v731/usb-wake-deployed-20261110/error-review/
```

Important files:

- `dmesg.txt` SHA-256 `87b44fc43f9b19eaf07c8d4c3780c95dacf71294833df80e25b790dc3776574f`
- `dmesg-err.txt` SHA-256 `ddb8dcd540f70513912244919fcd3c2d89fc456cba71914ce0387f9f7ff30679`
- `rc-status-all.txt` SHA-256 `dcc27f1a5f4a55193d688d704d163c4537f1bf8d8f5064474fdd9cf0506fe613`
- `rc.log` SHA-256 `72c6217dc03eaf1114794f6af88b89840381143345e5885874730fb62a125d23`
- `tinydm.log` SHA-256 `767bcac1faaa091a342ec8361c3e4d3c97fa286a811fa603aa4f5e9789a672fd`

## Debug-only state to remove later

The current root `elogind-inhibit` used to keep SSH available during
collection is not part of the product. Remove it after the next controlled
suspend test. The USB-wake udev rule is intended production policy; the
inhibitor is not.
