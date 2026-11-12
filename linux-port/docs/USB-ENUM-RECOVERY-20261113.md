# USB enumeration recovery after reboot (2026-11-13)

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

The deployed trial binary is:

```text
/usr/bin/usb-signaller
SHA-256 6ae3384d5bbd07614c2c3baf341159f8f1cd59e31d6e059b5bc1d31708f005b1
```

Rollback binary:

```text
/usr/bin/usb-signaller.bak-enum-20261113
SHA-256 a661c138fc27ae4cc262d2ded40d12da61f2fb7cc104012a9b2ff656ae61075f
```

The package metadata is now `0.4.3-r5`, but the APK has not yet been
built or installed through `apk`.

### samurai-usb-recover: bounded enumeration recovery

The recovery service now detects a host-attached UDC in `default` or
`address` state with a known link speed for 15 seconds. It first
reconnects the standard UDC `soft_connect`, then falls back to a bounded
full DWC3 unbind/bind within the existing two-attempt budget. It never
recovers an unattached UDC, and it does not turn a charger-only cable
into a data gadget.

Deployed script:

```text
/usr/sbin/samurai-usb-recover
SHA-256 ceabcb73c6a5815d6261ad43bdffe6767a67c0217a35ba60fd6174c589092b6f
```

Rollback copy:

```text
/usr/sbin/samurai-usb-recover.bak-enum-20261113
```

Offline tests:

```text
linux-port/diagnostics/test-usb-recover-enum-stuck.sh
linux-port/diagnostics/test-usb-recover-soft-link-lost.sh
linux-port/diagnostics/test-usb-recover-soft-first.sh
linux-port/diagnostics/test-usb-recover-mode-transition.sh
linux-port/diagnostics/test-usb-recover-generation.sh
```

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

## Remaining blocker

The host or physical port still does not complete SET_CONFIGURATION.
Windows has no present `VID_0525&PID_A4A1` instance; only stale hidden
instances remain. The next discriminators require a physical action or a
different host:

1. Replug on the same port after a full VBUS-off interval, then reset the
   Windows parent hub/port if the stale Code 43 state remains.
2. Try a motherboard-direct port instead of the old Genesys hub.
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
cp -p /usr/sbin/samurai-usb-recover.bak-enum-20261113 \
  /usr/sbin/samurai-usb-recover
rc-service usb-signaller restart
rc-service samurai-usb-recover start
```

No NV, persist, calibration or userdata partition was written.
