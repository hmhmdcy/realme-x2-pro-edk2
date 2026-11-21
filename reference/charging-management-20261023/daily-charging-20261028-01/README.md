# Samurai daily charging package

This directory is the active RMX1931 (realme X2 Pro) daily charging package.
The kernel driver owns charging safety and the userspace service only selects
the policy limits and explicitly enables AUTO after verification.

## Installed defaults

- Boot state is fail-safe: the managed driver binds inhibited with 500 mA input
  and 500 mA constant-current caps.
- The OpenRC service requests 900 mA input and 500 mA charge current, then sets
  `charge_behaviour=auto`.
- The source budget caps the effective input limit. The observed SMB/USB
  source is 500 mA, so `input_current_limit` reads 500000 even though the
  request is 900000.
- Full hold is owned by the kernel. At full charge it keeps the input converter
  available while CHG remains off.
- No trial guard or watchdog is installed.

## Verified device evidence

The latest cold boots bind `samurai-mp2650` automatically and start
`samurai-charging` in the default runlevel. A representative successful boot
has `taint=4096` only because the board driver is intentionally built
out-of-tree; there were no new warning, Oops, or stop errors.

The last verified active sample had:

```text
valid=1 online=1 protection_ok=1
latched=0 stop_error=0 fault=0 source_inhibit=0
effective_input_current_limit=500000
constant_charge_current=500000
charge_behaviour=auto
```

The USB delivery link itself is the control link. A true no-VBUS cold boot
cannot be automated from the current host without physically removing the
cable. The service path is written to accept that case (`online=0`, stay
inhibited, no 60-second budget failure) but this is not claimed as a measured
no-power boot.

## Build and install

Build the module in WSL with the ABI-matched k363 tree:

```sh
./build-managed.sh
```

On the device, create a complete rollback first and then install:

```sh
cd /root/charging-daily-20261028-03
sh ./prepare-backup.sh
sh ./install-daily.sh
/sbin/rc-service samurai-charging start
```

`install-daily.sh` checks the rollback SHA256SUMS before changing installed
files. The rollback directory is `/root/charging-daily-20261028-02-before`.

## Verification

The package hashes are checked locally with:

```sh
python3 verify-package.py
```

On the device, use the installed manifest and the read-only verifier:

```sh
/usr/sbin/samurai-charging hashes
python3 /root/charging-daily-20261028-03/verify.py
```

`hashes` reports the five installed file hashes without requiring a healthy
charger, which makes cold-boot diagnosis possible even when the service is
stopped or the battery is offline.

## Rollback

To return to the generic observer without overwriting the rollback snapshot:

```sh
echo 0-005c > /sys/bus/i2c/drivers/samurai-mp2650/unbind
rmmod samurai_mp2650
echo 0-005c > /sys/bus/i2c/drivers/mp2650/bind
```

The previous installed files are in
`/root/charging-daily-20261028-02-before`.

## Scope

This package covers ordinary 5 V charging, source-budget negotiation, thermal
bands, protection status, Full hold, stop/start, and cold-boot auto-start.
SuperVOOC, PD fast charging, and physical cable-removal tests are outside this
verified scope.
