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

The current image does not yet contain this generic fix.  Until it is
implemented and tested over repeated cold boots, a touchless boot can be
recovered by a normal reboot, but the random probe failure remains open.

## 2026-11-13 22:00 current status

Kernel `#7` boot `d9ec88d9-6556-4fc3-bbfe-d4f61368b3e4` has the touch
stack present again:

```text
input: Synaptics S3706A as /devices/platform/soc@0/cc0000.geniqup/c80000.i2c/i2c-4/4-0020/rmi4-00/input/input3
/dev/input/event3
```

The touch hardware and DTS are therefore healthy on this boot, but the
generic GPI-DMA retry/defer fix is still **not** deployed.  The failure
can recur on a cold boot; a normal reboot is still the recovery.  This
entry is not a permanent-fix claim.
