#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

root = Path('/home/cy122/pmos-samurai-kernel129/kernel')
source = root / 'drivers/power/supply/mp2650_charger.c'
reference = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel86/mp2650_charger.c')
body = source.read_bytes()
assert body == reference.read_bytes()
assert 'CONFIG_CHARGER_MP2650=y' in (root / '.config').read_text().splitlines()
assert (root / 'drivers/power/supply/mp2650_charger.o').is_file()
assert b'attempt < 3' in body and b'return -ENODATA;' in body
assert b'i2c_smbus_write' not in body and b'.set_property' not in body
result = dict(current_kernel=129, driver_sha256=hashlib.sha256(body).hexdigest(),
              corrected_87_observation_driver_already_in_current_source=True,
              configured_builtin=True, compiled_object_present=True,
              adc_retry_bound=3, inconsistent_adc_errno='ENODATA',
              charging_control_implemented=False,
              actual_power_supply_test_still_required=True)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel131/mp2650-current-source-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
