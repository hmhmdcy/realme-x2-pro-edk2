"""Validate native USB allowance and the actual automatically started service."""
from pathlib import Path
import hashlib
import json
import os
import runpy
import subprocess

assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k363+'
dt=Path('/sys/firmware/devicetree/base/soc@0/usb@a6f8800/usb@a600000/usb-psy-name')
assert dt.read_bytes()==b'samurai-usb-input\0'
with Path('/dev/disk/by-partlabel/boot').open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
assert digest==BOOT_SHA
lib=runpy.run_path('/usr/sbin/samurai-charging')
meta=lib['verify']()
for name,info in meta['modules'].items():lib['loaded_matches'](Path(info['target']),name.replace('-','_'))
assert Path('/sys/bus/i2c/devices/0-005c/driver').resolve().name=='samurai-mp2650'
assert Path('/etc/runlevels/default/samurai-charging').is_symlink()
assert Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y'
sample=lib['sample']()
assert all(sample[k]==1 for k in ['valid','online','protection_ok','desired_enable'])
assert not any(sample[k] for k in ['shadow','error','stop_error','latched','source_inhibit','fault'])
assert sample['age_ms']<2000
ps=Path('/sys/class/power_supply');source=ps/'samurai-usb-input';charger=ps/'mp2650-input'
data={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'boot_sha256':digest,'taint':int(Path('/proc/sys/kernel/tainted').read_text()),
    'sample':sample,'charger_status':(charger/'status').read_text().strip(),
    'source_type':(source/'usb_type').read_text().strip(),
    'source_budget_ua':int((source/'current_max').read_text()),
    'native_udc_allowance_ua':int((source/'input_current_limit').read_text()),
    'usb_config_max_power_ma':int(Path('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower').read_text()),
    'udc_state':Path('/sys/class/udc/a600000.usb/state').read_text().strip(),
    'actual_input_limit_ua':int((charger/'input_current_limit').read_text()),
    'actual_charge_current_ua':int((charger/'constant_charge_current').read_text()),
    'actual_pack_target_uv':int((charger/'constant_charge_voltage').read_text()),
    'battery_current_ua':int((ps/'bq28z610-0/current_now').read_text()),
    'protection_state':Path('/sys/devices/platform/samurai-gauge-protection/protection_state').read_text().strip(),
    'kernel_modules_loaded_and_exact':True,'service_boot_enabled':True,'native_provider_retained':True}
logs=subprocess.check_output(['dmesg'],text=True)
data['boot_fault_counts']={n:logs.count(n) for n in ['cannot create duplicate filename','refcount_t: underflow','WARNING:','Oops:']}
print(json.dumps(data),flush=True)
assert data['source_budget_ua']==1500000 and data['udc_state']=='configured'
# Compare the real native accepted callback ledger against this configured
# USB2 gadget. MaxPower alone is never used to authorize charger current.
assert data['native_udc_allowance_ua']==min(data['usb_config_max_power_ma'],500)*1000
assert data['actual_input_limit_ua']==900000 and data['actual_charge_current_ua']==250000
assert data['actual_pack_target_uv']<=8725000 and data['taint']==0
assert not any(data['boot_fault_counts'].values())
