# USB enumeration recovery after reboot (2026-11-13)

> 2026-11-13 12:25 update: the temporary `0.4.3-r5` trial is superseded
> by the packaged `usb-signaller 0.4.3-r9` main/openrc APKs. The package
> was verified with `apk verify`, installed, and passed three standard
> host→device cycles, plain supervisor restart, mode-cycle, four offline
> recovery regressions, an ordinary reboot at 62.298/63.813 seconds with
> both Wi-Fi and NCM SSH returning the same new boot ID, and USB NCM
> SSH. See
> [`USB-OTG-20261112`](USB-OTG-20261112.md) and
> `E:/edk2-samurai-out/standard-arm64-v731/otg-20261113-hostmode-fix/`.
> The enumeration-failure observations below remain historical evidence,
> not the current recovery state.

## Scope

This page records the post-reboot state of the RMX1931 USB2 OTG
candidate after Windows had previously stopped the NCM device with
Code 43 (`request for the USB device descriptor failed`). It separates
two issues:

1. a `usb-signaller` policy bug that downgraded the selected mode to
   charging-only when the host did not reach `configured`; and
2. the still-unresolved host/device enumeration failure itself.

Wi-Fi SSH was available throughout at `root@192.168.0.114`.

## Runtime evidence

| Item | Value |
| --- | --- |
| boot ID | `755f152f-b40b-4465-a147-565e4b247122` |
| kernel | `7.3.1-rmx1931-samurai-v731-usbwake-otg` |
| cable/host view | UDC `default`, `current_speed=high-speed` |
| NCM | `usb0` present, carrier 0 |
| VBUS | `mp2650-input/online=1` |
| Type-C | power `source [sink]`, data `host [device]` |
| Windows current PnP | no present `0525:a4a1`; older instances are `Unknown` |

UDC `default` means the host addressed the gadget but never completed
SET_CONFIGURATION. A known `current_speed` distinguishes this from a
dumb charger that only asserts VBUS.

Before the fix, `usb-signaller` waited 10 seconds for `configured`, then
failed the mode switch and fell back to Charging:

```text
Failed to enable gadget: usb-signaller-developer
(Gadget remained attached but UDC did not enter 'configured' state within 10s)
Mode: Charging
```

That removed the NCM gadget and also prevented the recovery service from
acting, because its monitor only considers Developer/Tethering modes.

## Fixes

### usb-signaller: preserve the selected mode

`0005-usb-signaller-preserve-mode-on-incomplete-enumeration.patch`
treats `default` and `address` as valid gadget-enable states. Full
`configured` remains the normal path; `not attached` retains the
existing offline-gadget path. The requested Developer/Tethering mode
now remains active so recovery can reconnect the public UDC interface.

The historical deployed trial binary is:

```text
/usr/bin/usb-signaller
SHA-256 6ae3384d5bbd07614c2c3baf341159f8f1cd59e31d6e059b5bc1d31708f005b1
```

Rollback binary:

```text
/usr/bin/usb-signaller.bak-enum-20261113
SHA-256 a661c138fc27ae4cc262d2ded40d12da61f2fb7cc104012a9b2ff656ae61075f
```

The `0.4.3-r5` trial was later superseded by packaged `0.4.3-r9`
(APK SHA-256
`fe4c960a22a92ef875fb2f5d9df5cf2880319bd281ed15fbadc18f62525c0c12`),
which includes patches 0001–0008 and was installed through `apk`.

### samurai-usb-recover: bounded enumeration recovery

The recovery service detects a host-attached UDC in `default` or
`address` state with a known link speed for 30 seconds. It first
reconnects the standard UDC `soft_connect`, then falls back to a bounded
full DWC3 unbind/bind within the existing two-attempt budget. It never
recovers an unattached UDC, and it does not turn a charger-only cable
into a data gadget.

Carrier loss while UDC remains `configured` is deliberately **not** a
recovery condition. On 2026-11-13 the earlier 12-second carrier-loss
path caused a self-amplifying loop: Windows toggled NCM alt setting,
`carrier` dropped to 0, recovery reset DWC3, and the fresh gadget made
Windows enumerate again. The 30-second policy and the removal of
`LINK_LOST`/`MODE_REATTACH` rebinds prevent that loop.

Deployed script:

```text
/usr/sbin/samurai-usb-recover
SHA-256 ad228238543e99d957309facb4fa6194e8b391dd2360ea4dc344660c67190c6f0e4ce71e1e5757f274357419ed2958709953ed7679a4fb1b68fa83b059bbef83
```

Rollback copy:

```text
/usr/sbin/samurai-usb-recover.bak-enum-20261113
/usr/sbin/samurai-usb-recover.bak-carrier-20261113
```

Offline tests:

```text
linux-port/diagnostics/test-usb-recover-enum-stuck.sh
linux-port/diagnostics/test-usb-recover-carrier-no-reset.sh
linux-port/diagnostics/test-usb-recover-generation.sh
linux-port/diagnostics/test-usb-recover-generation-no-success.sh
```

The carrier-no-reset regression asserts that a configured UDC with
carrier 0, including a gadget-generation change, produces no
`SOFT_RECOVER`/`RECOVER_BEGIN`, no UDC disconnect, and no DWC3 unbind.

## Deployed result

After restarting the candidate `usb-signaller`, `mode_request` remained
`developer_mode` and the Developer configfs gadget remained available.
The host still stayed in `default`/high-speed, so recovery performed two
bounded attempts:

```text
SOFT_ENUM_BEGIN reason=enumeration_stuck state=default speed=full-speed
SOFT_ENUM_FAIL reason=not_configured state=default
RECOVER_BEGIN attempt=1 reason=enumeration_stuck state=default
RECOVER_FAIL reason=not_configured state=default
SOFT_ENUM_BEGIN reason=enumeration_stuck state=default speed=high-speed
RECOVER_BEGIN attempt=2 reason=enumeration_stuck state=default
RECOVER_FAIL reason=not_configured state=default
```

This proves the mode/downgrade bug is fixed and the public recovery path
is armed. It does **not** prove that Windows enumerates again.

The first implementation still had an unbounded retry bug: each failed
DWC3 rebind recreated the configfs gadget, the monitor treated the new
generation as a user mode transition, and reset the two-attempt budget.
The log showed repeated `BUDGET_RESET`/`RECOVER_BEGIN` rounds even though
`seen_configured=0`. The fix is to retain the budget until the current
cable session has completed one real `configured`/carrier-1 enumeration:

```text
BUDGET_KEEP reason=no_configured attempts=2
```

The regression is
`test-usb-recover-generation-no-success.sh`.

## Isolation probes

The failure is not specific to the NCM descriptors:

Reproducible device-side tools:

```text
linux-port/diagnostics/probe-minimal-usb-gadget.sh
linux-port/diagnostics/trace-usb-enum.sh
```

1. A minimal standard configfs ACM gadget
   (`1d6b:0104`, one `acm.GS0` function) replaced the Developer gadget
   and was bound to `a600000.usb`.
2. UDC stayed `default`/high-speed for the full 30-second probe.
3. Windows reported root-hub port 5 as `Enumerating`, with VID/PID
   0000:0000 and no descriptor.
4. The probe restored `usb-signaller` and `samurai-usb-recover` cleanly.

Device-side `dwc3_event` tracing produced 163 events but zero
`dwc3_ctrl_req` events during a UDC reconnect. The repeating sequence was:

```text
Reset [U0]
usb_gadget_set_state ... state 5 (default)
Connection Done [U0]
Suspend [U3]
```

In other words, the host resets the link repeatedly, the DWC3 controller
enters default, and the host suspends before issuing a setup request. No
`GET_DESCRIPTOR` reaches the gadget.

Host-side isolation on Windows:

- `IOCTL_USB_GET_NODE_CONNECTION_INFORMATION_EX` confirmed port 5
  alternates between `DeviceEnumerating` and `NoDevice`;
- a non-elevated `IOCTL_USB_HUB_CYCLE_PORT` for port 5 was rejected by
  the root hub (`ERROR_NO_SUCH_DEVICE`);
- `IOCTL_USB_RESET_HUB` on the parent root hub succeeded; port 5
  restarted its reset/enumerating cycle but still returned no descriptor;
- `pnputil /problem` remained empty and no present `0525:a4a1` or
  `1d6b:0104` device appeared.

Device-side recovery at controller level also failed to change the
outcome:

- DWC3 was unbound/rebound;
- the SM8150 USB2 HS PHY `88e2000.phy`
  (`qcom,sm8150-usb-hs-phy`) was unbound/rebound;
- the UDC returned to `default`/high-speed and the host still issued no
  setup request.

Together, these rule out a `usb-signaller` NCM descriptor-only defect.
The remaining boundary is the physical cable, the host port, or a
device/PHY state that only a full power cycle clears. The current
software cannot distinguish those three without a known-good host or
cable.

## 2026-11-13 03:20-03:40 CST: recovery churn and core-link evidence

The phone rebooted at about 02:03 CST (boot ID
`755f152f-b40b-4465-a147-565e4b247122`, kernel
`7.3.1-rmx1931-samurai-v731-usbwake-otg`). The old recovery service
was still running the carrier-loss policy. A 20-second `dwc3_event`
trace showed **32 resets / 11 suspends**, while `usb-recover.log`
showed repeated `LINK_LOST state=configured carrier=0` followed by
`SOFT_RECOVER`/`RECOVER_BEGIN`. Each recovery rebuilt the gadget and
the host enumerated again, creating a self-amplifying reset loop.

After stopping the old recovery service, the UDC stayed `configured`
for most samples and the gadget rebuilds stopped. The 6-r10 script was
then deployed and restarted. Its monitor no longer treats carrier 0 as
a reset condition: a configured UDC with carrier 0, including a
configfs gadget-generation change, now only clears timers.

### Enumeration is intermittent, not descriptor-specific

Post-fix traces showed both extremes:

- one 30-second trace recorded **43 resets / 16 suspends** but only
  one `GET_DESCRIPTOR(Device, 64)`; the host never issued a complete
  setup sequence.
- another trace recorded **156 `dwc3_ctrl_req` events**: device
  descriptor, configuration descriptor, BOS, strings, SET_ADDRESS,
  SET_CONFIGURATION, `Set Interface(Intf=1, Alt=1)`, NCM class
  requests, and bulk endpoint activity.

So the host can complete full NCM enumeration and can move data, but
the link is repeatedly reset. The failure is not a missing NCM descriptor.

### Same failure at full-speed and with a minimal ACM gadget

Two clean configfs probes were run with `usb-signaller` and recovery
stopped:

| Probe | Result |
| --- | --- |
| `0525:a4a1`, one `ncm.usb0`, `max_speed=full-speed` | Windows read VID/PID, loaded `UsbNcm Host Device #5`; UDC `configured`, speed full-speed |
| `1d6b:0104`, one `acm.GS0`, `max_speed=full-speed` | Windows read VID/PID and created the ACM device; UDC `configured`, speed full-speed |

Both probes received **new USB addresses every ~2 seconds** (for
example 33, 34, 35, 36). The same happened to the production
high-speed NCM gadget. This rules out a defect specific to NCM,
`usb-signaller`, or the high-speed PHY tuning as the sole cause.

Type-C state was stable throughout: power role sink, data role
device, orientation `normal`, `mp2650-input/online=1`, no new
`pmic-typec` or PD kernel messages. The Type-C/TCPM layer is not
toggling the data link.

Windows' global USB selective-suspend policy was also tested. It was
enabled for AC and DC in the active power scheme. Disabling both for a
30-second observation window did not stop the loop: the trace still
showed 13 resets / 12 suspends / 12 enumerations, and the device logged
a `VBUS_OFF`/`VBUS_ON` pair. The policy was restored to its original
enabled state afterwards. This rules out the global selective-suspend
setting as the primary cause; the port is power-cycling or losing VBUS
independently of that policy.

### NCM data path can carry traffic

Windows created the NCM adapter and intermittently obtained the DHCP
lease `172.16.42.2/24`. The adapter also repeatedly went `Dormant`,
lost its IPv4 address, or disappeared from PnP. A source-bound TCP
connection eventually received:

```text
SSH-2.0-OpenSSH_10.6
```

This proves the phone's NCM gadget and the cable can carry real
traffic. It does not prove a stable link.

Windows also routes `172.16.42.1` through the Mihomo TUN interface
(`198.18.0.1`), not the NCM adapter. Direct tests therefore need a
source-bound socket and OpenSSH must use `ProxyCommand=none`
`ProxyJump=none`; even then the address disappears during the reset
windows. This is a host-routing confounder, not a phone-side USB defect.

### Current conclusion

The software recovery loop is fixed, but the physical link still
re-enumerates every few seconds for every gadget type and at both
full-speed and high-speed. The remaining boundary is the physical
cable, the phone's Type-C connector, or Windows root-hub port 5. A
known-good cable and a different host port are required before
continuing OTG host acceptance.

### Wi-Fi remains independent of the USB reset loop

A 60-second unattended access check ran 12 Wi-Fi SSH probes at 5-second
intervals while DWC3 tracing recorded **23 resets / 24 suspends**. All
12 probes returned exit code 0, the boot ID stayed
`755f152f-b40b-4465-a147-565e4b247122`, and `mp2650-input/online`
stayed 1. The failing USB link therefore does not take out the Wi-Fi
management path; unattended recovery access is still available.

### Port 6 cross-check (2026-11-13 05:39-05:41 CST)

The phone was moved from root-hub port 5 to port 6. The same failure
followed it: port 6 showed new addresses 97/98/99 and then
`Enumerating`/`NoDevice`, while a 60-second DWC3 trace recorded
**114 resets / 110 suspends**. In the same window, the keyboard on
port 5 stayed at address 95 and remained `Connected` for the full
cross-check:

```text
05:41:23-05:41:46 PORT 5 Connected VID=3837 PID=3003 ADDR=95
05:41:36 PORT 6 Connected VID=0525 PID=A4A1 ADDR=43
05:41:40 PORT 6 Connected VID=0525 PID=A4A1 ADDR=44
05:41:42 PORT 6 NoDevice
05:41:44 PORT 6 Connected VID=0525 PID=A4A1 ADDR=50
05:41:46 PORT 6 Enumerating
```

The host root hub and both physical ports can sustain a stable device;
the failure follows the phone/cable, not a specific host port. The next
physical discriminators are (in order): flip the phone-side Type-C plug
180 degrees without changing the cable, then replace the cable, then
inspect/clean the phone Type-C receptacle.

### 2026-11-13 05:56-06:10 CST: link recovered, both SSH paths stable

After the user rebooted and changed the physical setup, the phone came
back with a new boot ID
`709bd3bc-9684-471b-ab49-8fdf04eebc0d` and a stable USB link on
root-hub port 6. Measurements:

```text
port 6: 0525:a4a1, high-speed, address 13 unchanged for >40 s
DWC3 60 s: RESET=0 SUSPEND=0
UDC: configured, usb0 carrier=1
USB NCM SSH: success (source-bound 172.16.42.2)
8 MiB scp over NCM: SHA-256 match
Wi-Fi SSH: success at 192.168.0.114
```

The 8 MiB file was sent over the USB NCM interface and its phone-side
SHA-256 was
`6ae125335d7ecf62ad55678cd0c9b3d9f4f8f2f6288aec5ac8cd7b1ed8069ea8`,
matching the host copy. USB and Wi-Fi SSH were usable simultaneously.
This closes the immediate "USB or Wi-Fi, but not both" failure for the
current boot and cable setup.

### Wi-Fi toggle failure: stuck Plasma Mobile KCM

The user-reported "Wi-Fi off then on does not come back" was reproduced
while USB SSH was healthy. `rfkill` showed phy0 soft-blocked and
`wlan0` stayed `unavailable`/`DOWN`. NetworkManager's log showed
`radio-control wireless-enabled:on/off` from **pid 5209**, repeatedly,
many times per second. The process was:

```text
/usr/sbin/plasma-settings -m kcm_mobile_wifi
```

The Plasma Mobile Wi-Fi KCM was stuck in a radio-control feedback loop,
not an ath10k firmware failure. The loop is a QML bug in
`plasma-nm`'s `kcm_wifi_mobile`: `onCheckedChanged` handled both
user and programmatic `checked` changes, and the explicit
`Qt.binding()` re-armed the switch before NetworkManager applied the
previous radio write. The standardized UI-layer fix is
`onToggled: handler.enableWireless(checked)` with the declarative
binding left in place; see
[`WIFI-KCM-20261113`](WIFI-KCM-20261113.md) and
`linux-port/packages/plasma-nm/`. Killing that settings process, then:

```sh
rfkill unblock wifi
nmcli radio wifi on
ip link set wlan0 up
```

restored `wlan0`, DHCP `192.168.0.114/24` and Wi-Fi SSH. A subsequent
plain `nmcli radio wifi off` / `on` cycle also recovered normally, so
the NetworkManager/wpa_supplicant stack is healthy.

The repeatable recovery script is
`linux-port/packages/samurai-platform/usr_sbin_samurai-wifi-recover`
(installed as `/usr/sbin/samurai-wifi-recover`); it kills the stuck KCM,
clears rfkill, enables the radio, brings `wlan0` up and waits for
the saved Wi-Fi connection (discovered from NetworkManager, not a
hard-coded profile name) to connect without restarting NetworkManager
(so the USB NCM SSH session remains available).

The recovery script is an emergency backend only. The normal fix belongs
to the desktop UI layer, not to `samurai-platform`.

## Remaining blocker

Windows root-hub port 5 still enters a reset/re-enumeration loop. It
sometimes completes full SET_CONFIGURATION and NCM data transfer, and
sometimes resets without issuing any setup request. The link is not
stable enough for NCM, OTG host or suspend/wake acceptance. The next
discriminators require a physical action or a different host:

1. Replace the USB cable with a known-good data cable; clean/inspect
   the phone's Type-C connector.
2. Move the phone to a different motherboard port (not root-hub port 5)
   and, if possible, to a Linux host.
3. Boot a Linux host with `usbmon`; capture the first
   `GET_DESCRIPTOR(Device)` and address/SET_CONFIGURATION sequence. That
   separates a host-port refusal from a gadget descriptor/controller bug.
4. Only after enumeration reaches `configured` and carrier 1, continue
   Type-C orientation, OTG peripheral and suspend/wake acceptance.

Do not record this incident as a successful NCM reboot, OTG host pass or
USB wake pass.

## Rollback

Stop the recovery service, restore both backup binaries, and restart
`usb-signaller`:

```sh
rc-service samurai-usb-recover stop
cp -p /usr/bin/usb-signaller.bak-enum-20261113 /usr/bin/usb-signaller
cp -p /usr/sbin/samurai-usb-recover.bak-carrier-20261113 \
  /usr/sbin/samurai-usb-recover
rc-service usb-signaller restart
rc-service samurai-usb-recover start
```

No NV, persist, calibration or userdata partition was written.
