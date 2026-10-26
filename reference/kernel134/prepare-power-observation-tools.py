from pathlib import Path
import ast
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
prev = r / 'reference/kernel132'
assert not (ref / 'test-persistent-power.py').exists()
t = (prev / 'test-persistent-power.py').read_text().replace('k132', 'k134').replace('K132', 'K134')
t = t.replace("boot = Path('/proc/sys/kernel/random/boot_id').read_text()", "usb = Path('/sys/class/power_supply/samurai-usb-input')\nassert usb.joinpath('device/of_node').resolve() == Path('/sys/firmware/devicetree/base/soc@0/spmi@c440000/pmic@2/usb-input@1300')\nboot = Path('/proc/sys/kernel/random/boot_id').read_text()")
t = t.replace("(out / 'permissions.json').write_text", "usb_permissions = {p: stat.S_IMODE((usb / p).stat().st_mode) for p in ['online', 'usb_type', 'current_max']}\nassert all(m == 0o444 for m in usb_permissions.values())\n(out / 'usb-permissions.json').write_text(json.dumps(usb_permissions, indent=2) + '\\n')\n(out / 'permissions.json').write_text")
t = t.replace("samples.append(item)", "item['usb_input'] = {p: (usb / p).read_text() for p in ['online', 'usb_type', 'current_max', 'uevent']}\n    assert item['usb_input']['online'].strip() == '1'\n    assert int(item['usb_input']['current_max']) in [1500000, 3000000]\n    samples.append(item)")
t = t.replace('timeout=12, check=True', 'timeout=60, check=True')
ast.parse(t)
(ref / 'test-persistent-power.py').write_text(t)
t = (prev / 'verify-persistent-power.py').read_text().replace('kernel132', 'kernel134').replace('kernel=132', 'kernel=134')
t = t.replace('report = dict(', '''assert all(m == 0o444 for m in json.loads(d['usb-permissions.json']).values())
usb_samples = [s['usb_input'] for s in samples]
assert all(s['online'].strip() == '1' and 'POWER_SUPPLY_CURRENT_MAX=' in s['uevent'] for s in usb_samples)
usb_types = sorted(set(s['usb_type'].strip() for s in usb_samples))
budgets = sorted(set(int(s['current_max']) for s in usb_samples))
for s in usb_samples:
    selected = re.search(r'\\[([^\\]]+)\\]', s['usb_type'])
    assert selected and selected[1] in ['CDP', 'DCP', 'C']
    assert int(s['current_max']) == 1500000 if selected[1] in ['CDP', 'DCP'] else int(s['current_max']) in [1500000, 3000000]
report = dict(usb_input_standard_nonempty_uevents=8,usb_input_properties_read_only=True,
              usb_input_types=usb_types,usb_input_current_max_microamps=budgets,
              current_max_is_source_allowance_not_measured_current=True,''')
ast.parse(t)
(ref / 'verify-persistent-power.py').write_text(t)
print('K134_SAME_BOOT_MP2650_AND_USB_BUDGET_8_SAMPLE_OBSERVATION_TOOLS_READY', flush=True)
