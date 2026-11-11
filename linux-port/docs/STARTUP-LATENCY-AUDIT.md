# Startup Latency Audit

Date: 2026-11-08

This audit covers the boot path from the ordinary reboot request through the
first usable SSH session. It does not include external-power-removed cold
boot, GRUB, or desktop interaction.

## Measured result

All timings below are from PowerShell-to-device `TCP/22` plus strict-key SSH
on the same ordinary boot. The raw JSON is local evidence, not a public
scenario capture.

| State | Wi-Fi SSH after request | NCM SSH after request | Notes |
| --- | ---: | ---: | --- |
| Before fix | 100.863 s | 35.862 s | fixed `sleep 45` held `samurai-radio` |
| Direct fast candidate | 54.301 s | 33.705 s | bounded MPSS state poll |
| `samurai-platform` 5-r17 | 57.288 s | 36.689 s | signed package, ordinary reboot |

On the r17 boot, the device-side uptime at first SSH was approximately 26
seconds for Wi-Fi and 7 seconds for NCM. The host saw the NCM PnP device and
DHCP lease at about the same time as the NCM SSH result. This removes the
previous fixed 45-second Wi-Fi penalty; the remaining Wi-Fi interval is
dominated by the real firmware/remoteproc preparation and association.

The r17 NCM regression's device dmesg shows the normal case explicitly:
`wlan0` authenticated at 24.68 seconds and associated at 24.76 seconds, while
first Wi-Fi SSH was recorded at about 26 seconds of device uptime. The later
86.6-117 second host results therefore cannot be explained by
`samurai-wifi` still holding a fixed 45-second sleep.

Evidence:

- pre-fix: `E:/edk2-samurai-out/standard-arm64-v731/network-reboot-readiness-20261108-r2.json`
- direct candidate: `E:/edk2-samurai-out/standard-arm64-v731/network-reboot-readiness-fast-ready-20261108.json`
- r17: `E:/edk2-samurai-out/standard-arm64-v731/network-reboot-readiness-r17-20261108.json`
- r17 full runtime: `E:/edk2-samurai-out/standard-arm64-v731/wifi-fast-ready-20261108/runtime-camera-r17.json`
- r17 package: `E:/edk2-samurai-out/standard-arm64-v731/wifi-fast-ready-20261108/samurai-platform-5-r17.apk`

## Code changes

`samurai-wifi` previously executed an unconditional `sleep 45` after starting
MPSS and bringing up `wlan0`. That blocked `wpa_supplicant` and
NetworkManager even when the standard remoteproc was already running.

The fixed sleep is now a bounded poll of the standard MPSS `state`:

```text
while state != running:
    wait one second, up to SAMURAI_WIFI_STATE_WAIT (default 45)
```

The existing TFTP, RMTFS, QRTR, NV checksum and WLAN-address checks remain.
The package source is `linux-port/packages/samurai-platform/usr_sbin_samurai-wifi`;
the installed r17 payload has SHA-256
`b6db019983adfe73c45b0df7dfe237bdf7cc6625151d6048b104e1dc1c873778`.

## postmarketOS/Nura parity check

The current official pmaports tree was checked at commit
`b5810eb2f3b24ce380a00c54569236f5559f78b1` (2026-11-07). The upstream
`postmarketos-base-openrc` starts `unudhcpd.usb0` in the `boot` runlevel and
`sshd` in `default`; the base UI package adds `wpa_supplicant` and the
NetworkManager integration, while the Plasma UI package starts
NetworkManager, Bluetooth, ModemManager and the other desktop services as
independent default-runlevel services. Its `tinydm` configuration has no
`rc_need`/`rc_after` ordering behind optional hardware enumeration.

The official sleep policy is also narrower than this board's old policy:
`postmarketos-base-ui` selects `sleep-inhibitor` with only
`ssh-session-open` and `apk-running` by default. A USB carrier being present
is not itself a sleep lock. This means the panel can be off while an active
SSH session keeps the system awake; a charging-only USB cable does not keep
the phone awake forever.

That comparison exposed two remaining board-level constraints:

1. `samurai-desktop` ordered `tinydm` after ModemManager and Bluetooth. In
   the r17 dmesg, Bluetooth setup ran around 82.6-83.9 seconds, so the
   graphical session could be delayed even though Wi-Fi SSH was already up.
   The `samurai-desktop` 4-r9 candidate removes that ordering; Plasma starts
   while optional radio services enumerate.
2. The board config loaded `samurai-usb-sleep-guard` whenever `usb0` carrier
   was up. 5-r20 made it opt-in; 5-r24 removes it from the production
   package entirely. The only installed policy is the standard
   `ssh-session-open`/`apk-running` pair; carrier-only keep-awake lives in
   `linux-port/debug/sleep-policy/`.

Both are offline candidates. They do not replace the installed r17/r8
combination until the handset is back online, the signed APKs are installed,
and an ordinary reboot plus the boundary/runtime gates pass.

## SSC readiness

The same audit found a second unconditional delay: `samurai-ssc` slept for
20 seconds after `hexagonrpcd` appeared, before probing the real sensor
service. On the earlier boot `4f95b334-610a-46b0-b442-ed27b4526a1f`, the
FastRPC device was created at `03:32:32.424` and the first accelerometer
probe completed at `03:32:54.536` (22.1 seconds later). The fixed sleep was
replaced with a bounded wait for the standard QRTR SSC service (service 400)
plus bounded retries of the real accelerometer/light readiness probes.

On the final ordinary boot `f6113e67-cee2-4708-b2cd-c004344e0eb0`, the
FastRPC device appeared at `03:49:13.408`, the accelerometer probe completed
at `03:49:19.084`, and the light probe completed at `03:49:21.088`. The
`default` runlevel finished in 26 seconds on three consecutive boots,
down from 42 seconds on the earlier boot, with `samurai-ssc` started,
`taint=0`, no runtime warnings and the full skip-camera gate passing.

The device-side Wi-Fi log still reports `WIFI_READY` at about 18.5-18.8
seconds of uptime. In later host-side measurements the first Wi-Fi TCP/22
was 86.6-117.0 seconds while NCM remained 33.7-33.8 seconds; one boot also
showed a local Choice deauthentication around 70 seconds followed by a
successful reassociation. That is a host/AP association or DHCP-path
variation, not the removed SSC sleep, and it remains an external-link
acceptance item.

Evidence:

- `E:/edk2-samurai-out/standard-arm64-v731/ssc-fast-20261108/runtime-ssc-fast-20261108.json`
  (SHA-256 `df2c1bb444c3a384728f9d58265dbd57775f24aedda446ec9addeae324f5e562`)
- `E:/edk2-samurai-out/standard-arm64-v731/ssc-fast-20261108/boundary-ssc-fast-20261108.log`
  (SHA-256 `2b3085b1aec05a2ace6840c549c1246479838ab46898f0e29eb1fb9b599d8b23`)
- `E:/edk2-samurai-out/standard-arm64-v731/network-reboot-ssc-final-20261108.json`
  (SHA-256 `6dbfcd1fecba04d3f1d86ab3050d98ba67b402467fef0dcfdfd358613d6105d8`)

## kexec safety probe

The qcom hardware watchdog was independently verified with `wdctl`: identity
`qcom_wdt`, timeout 30 seconds, no magic-close capability. A controlled
armed-and-expired test forced a reboot from
`1b9dacbc-7ac1-4600-8738-8dfee46f5206` to
`7a1b5d79-b02f-43dc-a18f-4c7e6dbfccaa` on the normal production images.

The live-FDT kexec path was then exercised with the exact production Image
and command line. It reached boot `a7f86ffb-1079-4cec-a933-e448b85a13af`,
but is **not an acceptance result**: the new kernel reported `taint=512`
from DSI PHY clock disable/unprepare warnings, the SLPI watchdog fired
(`-110`), and GPU/GMU initialization timed out. A normal reboot immediately
returned to the clean production state (`4f95b334...`, `taint=0`).

The guarded harness is
`linux-port/diagnostics/run-kexec-standard-smoke.sh` (SHA-256
`854336dd6a81e43c339bcdd968bd3b0b78b6c4eb4aae3d4e610ec660a9be82b6`).
Its kexec dmesg is retained at
`E:/edk2-samurai-out/standard-arm64-v731/kexec-smoke-20261108/kexec-standard-smoke.dmesg`
(SHA-256 `1a875800d6a7b74a7b7ccad49de8d52cf618412a8b283032a9b65a2e0aaba298`).

A second preflight used the clock-RBCPR Image and a live-FDT copy whose
`/chosen/bootargs` was rewritten without `clk_ignore_unused` (FDT SHA-256
`1bccb9276996fb3dcbd7e7810c43364e76db6944b368166ae647172eca7ab12a`).
The harness reported `kexec_loaded=1` and `watchdog=armed`, but the handset
did not return over Wi-Fi, NCM or fastboot for more than 255 seconds. This
left the device requiring a physical power cycle, while the persistent boot
and FAT were unchanged. The qcom watchdog is therefore useful for a simple
stuck process, but is **not a reliable kexec rollback**: kexec can pass
control into a kernel that hangs before the watchdog service is re-owned.

Consequently the clock-RBCPR candidate remains unflashed. A no-flag kexec
preflight must not be attempted unattended again; the next attempt requires
physical access to power-cycle the handset, followed by a paired persistent
flash, ordinary reboot and external-power-removed cold boot before
`clk_ignore_unused` can be removed.

## Remaining blockers found by static audit

- `samurai-bluetooth boot()` had a historical fixed uptime-60 wait, a
  10-second sleep and a display wait. The r18/r20 source replaces those with
  the Wi-Fi-bootstrap/display gates plus optional bounded overrides; the
  installed r17 package still contains the old code, and its
  `/etc/init.d/bluetooth` calls `start`, not `boot`. The candidate is not
  installed or boot-tested, so it must not be treated as a device-proven fix.
- The distribution `pipewire-launcher.sh` waited indefinitely for
  `/usr/bin/pipewire`. The offline `pipewire-common` 1.6.9-r4 source now uses
  a bounded 15-second readiness window and exits nonzero on failure. It is
  outside the measured SSH/NCM path and has not been rebuilt or installed.
- `samurai-bluetooth start` and `samurai-wifi` still use bounded hardware
  waits (30 seconds for `hci0`, 60 seconds for the SoC serial, 120 seconds
  for UFS/WLAN). These are now bounded failure windows, not unconditional
  delays; removing them would make early-hardware races less diagnosable.
- The `samurai-platform` 5-r20 source removes the remaining soft
  `sshd -> samurai-usb`, `NetworkManager -> samurai-radio` and
  `ModemManager -> samurai-radio` startup gates. The official services start
  independently; the board daemons now rely on udev/QRTR discovery instead.
  This is an offline candidate, so the next ordinary boot and the timeline
  collector must prove Wi-Fi association, DHCP and SSH still converge.
  An isolated bubblewrap test using r17-like `conf.d` fixtures confirmed that
  the install hook leaves NetworkManager/sshd with `rc_need="dbus"` only,
   removes ModemManager's hard radio dependency. 5-r24 also removes the
   remaining local wpa_supplicant/ModemManager ordering so the package
   restores the official base-ui files; verify that candidate before
   deployment.
- The full `verify-v731-final-runtime.py` gate must still run after OpenRC
  default completes, not immediately after the first SSH response. The 4-r9
  candidate removes the artificial Bluetooth/ModemManager ordering, but the
  actual KWin/Plasma startup interval remains a runtime measurement item.

Official source references:

- <https://gitlab.postmarketos.org/postmarketOS/pmaports/-/blob/b5810eb2f3b24ce380a00c54569236f5559f78b1/main/postmarketos-base-ui/APKBUILD>
- <https://gitlab.postmarketos.org/postmarketOS/pmaports/-/blob/b5810eb2f3b24ce380a00c54569236f5559f78b1/main/postmarketos-base-ui/rootfs-etc-sleep-inhibitor.conf>
- <https://gitlab.postmarketos.org/postmarketOS/pmaports/-/blob/b5810eb2f3b24ce380a00c54569236f5559f78b1/main/postmarketos-base/postmarketos-base-openrc.post-install>

The first SSH path is now fast relative to the hardware preparation, but the
external-power-removed cold-boot and repeated cold-boot acceptance remains
open. The fastboot `VID_0000&PID_0001` Code 43 condition is a separate ABL
USB enumeration issue and is not fixed by this startup work.

To separate device-side readiness from the Windows host's first-ARP/DHCP
window, run this read-only collector after the next boot:

```sh
sh linux-port/scripts/collect-network-startup-timeline.sh
```

It records the current `/proc/uptime`, OpenRC service state, process ages,
`dmesg` Wi-Fi/NCM/QRTR lines, `wlan0` association, DHCP/lease state, USB UDC
state, sleep locks and SSH sockets. It does not reboot or change the network.
