#!/usr/bin/python3
"""Read-only verification of the daily charging path."""
import json
import os
import subprocess
from pathlib import Path

PSY = Path('/sys/class/power_supply')
USB = PSY / 'samurai-usb-input'
MP = PSY / 'mp2650-input'
CLIENT = Path('/sys/bus/i2c/devices/0-005c')


def integer(path):
    return int(path.read_text().strip())


def main():
    assert os.geteuid() == 0
    assert os.uname().machine == 'aarch64'
    assert (CLIENT / 'driver').resolve().name == 'samurai-mp2650'
    tcpm = next(PSY.glob('tcpm-source-psy-*'))
    online = integer(USB / 'online') == 1
    effective_input = integer(MP / 'input_current_limit')
    assert integer(MP / 'constant_charge_current') == 500000
    assert 'auto' in (MP / 'charge_behaviour').read_text()
    telemetry = {
        key: int(value) for key, value in
        (item.split('=', 1)
         for item in (CLIENT / 'telemetry').read_text().split())
    }
    assert telemetry['valid'] == 1, telemetry
    if online:
        assert telemetry['online'] == 1
        assert telemetry['protection_ok'] == 1
        assert integer(USB / 'current_max') >= 50000
        assert integer(tcpm / 'current_max') >= 50000
        assert integer(tcpm / 'current_now') >= 50000
        assert 50000 <= effective_input <= 900000
    else:
        assert telemetry['online'] == 0, telemetry
    for key in ('latched', 'stop_error', 'fault', 'source_inhibit'):
        assert telemetry[key] == 0, (key, telemetry)
    assert integer(MP / 'constant_charge_current') <= 500000
    assert effective_input <= 900000
    if online:
        assert telemetry['budget_ua'] >= 50000, telemetry
    service = json.loads(subprocess.check_output(
        ['/usr/sbin/samurai-charging', 'status'], text=True))
    assert service['managed'] is True, service
    result = {
        'passed': True,
        'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'release': os.uname().release,
        'driver': 'samurai-mp2650',
        'online': online,
        'usb_current_max': integer(USB / 'current_max'),
        'tcpm_current_max': integer(tcpm / 'current_max') if online else None,
        'tcpm_current_now': integer(tcpm / 'current_now') if online else None,
        'requested_input_current_limit': 900000,
        'effective_input_current_limit': effective_input,
        'constant_charge_current': integer(MP / 'constant_charge_current'),
        'telemetry': telemetry,
        'service': service,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
