# S3706 touch boot-time disappearance (2026-11-13)

## Symptom

One boot had no touch input device at all.  The panel and Plasma session
were still running, but `/proc/bus/input/devices` contained only the
power key, haptics, GPIO keys and headset jack.  A normal reboot restored
touch.

## Evidence

The failing boot log contains:

```text
[0.435] geni_i2c c80000.i2c: Bus frequency not specified, default to 100kHz.
[0.724] gpi c00000.dma-controller: cmd: EV ALLOCATE completion timeout:2
[0.724] gpi c00000.dma-controller: error with cmd:EV ALLOCATE ret:-5
[0.724] gpi c00000.dma-controller: error alloc_ev_chan:-5
[0.725] geni_i2c c80000.i2c: error -ENODEV: Failed to get rx DMA ch
```

The subsequent path is therefore absent:

```text
c80000.i2c -> i2c-4 -> rmi4-00 -> Synaptics S3706A -> /dev/input/event3
```

The board DTS and RMI4 binding are not the failure: the touch node has the
correct I2C address, TLMM122 interrupt, TLMM54 reset and both supplies.
On the successful boot the same DTB produces:

```text
c80000.i2c/driver -> geni_i2c
input3/name = Synaptics S3706A
```

## Layered diagnosis

| Layer | Finding |
| --- | --- |
| S3706/RMI4 | Driver and DT wiring are correct; no input device is created only because its I2C parent never probes |
| GENI I2C (`c80000.i2c`) | One-shot probe treats the transient DMA failure as fatal `-ENODEV` and does not retry |
| Qualcomm GPI DMA (`c00000.dma-controller`) | The first event-ring allocate command did not complete inside the driver's 250 ms timeout |
| Board DTS | No hardware difference is required; this is not an RMX1931-only wiring issue |

The precise reason the GPI controller loses the first command completion
has not yet been proven.  The reproducible software defect is the lack of
a bounded retry/defer in the GENI client after that transient failure.

## Correct fix boundary

The fix belongs in the generic `i2c-qcom-geni`/GPI path, not in the S3706
driver or in a board-specific boot script.  A suitable implementation is
to translate this specific probe-time DMA failure into `-EPROBE_DEFER`, or
to perform a small bounded retry after the GPI controller has finished
initialising.  A permanent boot-time `echo ... > bind` workaround would
mask the race and is not the production solution.

Before 2026-11-14 the deployed image did not contain this generic fix.
Until it is tested over repeated cold boots, a touchless boot can still
be recovered by a normal reboot; the 2026-11-14 deployment and its
current evidence are recorded below.

## 2026-11-13 22:00 current status

Kernel `#7` boot `d9ec88d9-6556-4fc3-bbfe-d4f61368b3e4` has the touch
stack present again:

```text
input: Synaptics S3706A as /devices/platform/soc@0/cc0000.geniqup/c80000.i2c/i2c-4/4-0020/rmi4-00/input/input3
/dev/input/event3
```

The touch hardware and DTS are therefore healthy on this boot.  The
generic GPI-DMA retry/defer fix described above was deployed on
2026-11-14; the 22:00 entry above is the pre-fix state and must not be
read as the current deployment.

## 2026-11-14 fix deployed

`0027-i2c-qcom-geni-defer-transient-gpi-dma.patch` is applied to the
`standard-arm64-v7.3.1` tree.  It changes two generic paths:

- `i2c-qcom-geni`: when the DT has `dmas` and `dma_request_chan()`
  returns the dmaengine-collapsed `-ENODEV`, return `-EPROBE_DEFER`
  instead of failing the adapter probe permanently.
- `gpi`: when `gpi_ch_init()` fails, free the just-allocated transfer
  ring and reset the channel/GPII state so a later deferred probe does
  not leak a coherent ring or reuse a half-initialised GPII.

Deployed candidate:

```text
kernel release: 7.3.1-rmx1931-samurai-v731-usbwake-otg
kernel build:   #8 Sat Nov 14 09:46:41 CST 2026
Image sha256:   29c8d27c64b9f3bb11bbf6b94bcd211e88aa3ad4a8d31955b37b54d622d8a739
logdump sha256: 125436109e7bb950bf608610ffc3dca656638764e695f52eda843eaf16d70dbb
boot sha256:    4520915183bbdf91bf606c1f2c711097a7a686c5e4666298e8bd1665a44036f1
```

Only the kernel FAT (`logdump`) was written; the boot carrier and DTB
inside it are byte-identical to the previous deployment.  Ten actual
warm reboots each produced a new boot ID, retained `Synaptics S3706A`
as `input4`/`event4`, and had zero `EV ALLOCATE` / `alloc_ev_chan` /
`Failed to get rx DMA` messages.  `taint` remained 512
(`0x200`), the same pre-existing warning state.

Evidence:

```text
E:\edk2-samurai-out\standard-arm64-v731\touch-gpi-probe-20261114\
  evidence\state-after.txt
  evidence\reboot-soak.log
  evidence\image-build.log
  evidence\flash.log
```

Still open: a real cold boot with external power removed has not been
performed on this candidate, and long-term/edge/multi-touch behaviour
has not been re-accepted.  The 10 warm reboots do not replace that
hardware acceptance.

Rollback pair for this candidate:

```text
previous logdump: 98addba8b234936ab19802d62b5b60e0f9abf13a6453efbd14b79f52318ad4c0
previous Image:   042ae1e2e9048e3d3f93f2b010721a284647bf35914804d6669e861df19cce22
boot:             4520915183bbdf91bf606c1f2c711097a7a686c5e4666298e8bd1665a44036f1
```

The previous logdump image is
`E:\edk2-samurai-out\standard-arm64-v731\otg-20261113-vbus-reg-r3\logdump-vbus-reg.img`;
the boot carrier was not changed by this deployment.
