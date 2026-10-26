"""Change the USB descriptor only during the user's physical disconnection.
No budget injection, charger control, gadget unbind or service invocation.
"""
from pathlib import Path
import hashlib
import json
import os
import runpy
import time
import traceback

directory = Path(__file__).resolve().parent
config = json.loads((directory / 'request-private.json').read_text())
power = Path('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower')
udc = Path('/sys/class/udc/a600000.usb/state')
live = runpy.run_path('/usr/sbin/samurai-charging')['live']

def status(phase, **fields):
    tmp = directory / 'status-next.json'
    tmp.write_text(json.dumps({'phase': phase, 'pid': os.getpid(), **fields}))
    tmp.replace(directory / 'status.json')

try:
    boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
    assert boot == Path(config['guard']).read_bytes()
    assert hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest() == config['manifest_sha256']
    assert power.read_text().strip() == '100'
    assert udc.read_text().strip() == 'configured'
    status('armed-awaiting-physical-detach', descriptor_ma=100)
    start = time.monotonic()
    while time.monotonic() - start < 600:
        # UDC state can remain configured while physically unplugged on this
        # board. Require agreement of the real PMIC and MP2650 Power Good.
        source = Path('/sys/class/power_supply/samurai-usb-input/online')
        if source.read_text().strip() == '0':
            if not live.registers()['13'] & 2 and source.read_text().strip() == '0':
                power.write_text('500')
                assert power.read_text().strip() == '500'
                status('applied-while-physically-detached', descriptor_ma=500,
                       host_acceptance_pending=True, budget_or_charger_writes=0)
                break
        time.sleep(.25)
    else:
        status('timeout-no-descriptor-change', descriptor_ma=int(power.read_text()))
except BaseException:
    (directory / 'failure-private.txt').write_text(traceback.format_exc())
    status('failed')
    raise
