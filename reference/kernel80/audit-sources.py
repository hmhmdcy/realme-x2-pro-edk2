from pathlib import Path
import hashlib
import json

w = Path('/mnt/e/RealmeX2Pro edk2')
ref = w/'reference/kernel80'
stock = Path('/mnt/e/edk2-samurai-out/kernel76')
research = stock/'charging-research'
linux = Path('/home/cy122/x2pro-linux/linux')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not (ref/'charging-source-audit.json').exists()
manifest = json.loads((w/'reference/kernel76/stock-source-manifest.json').read_text())
mapping = {
    'drivers/power/oppo/gauge_ic/oppo_bq27541.c':stock/'stock-oppo_bq27541.c',
    'drivers/power/oppo/gauge_ic/oppo_bq27541.h':stock/'stock-oppo_bq27541.h',
    'drivers/power/oppo/charger_ic/oppo_mp2650.c':stock/'stock-oppo_mp2650.c',
}
files = {}
for name, p in mapping.items():
    expected = manifest['files'][name]
    assert sha(p) == expected['sha256'] and p.stat().st_size == expected['bytes']
    files[name] = expected
header = mapping['drivers/power/oppo/gauge_ic/oppo_bq27541.h'].read_text()
for expected in ('DEVICE_TYPE_BQ28Z610', '0xFFA5', 'BQ28Z610_MAC_CELL_VOLTAGE_EN_ADDR',
                 'BQ28Z610_MAC_CELL_VOLTAGE_CMD', 'BQ28Z610_MAC_CELL_VOLTAGE_ADDR'):
    assert expected in header
gauge = mapping['drivers/power/oppo/gauge_ic/oppo_bq27541.c'].read_text()
assert 'bq28z610_get_2cell_voltage' in gauge and 'usleep_range(1000, 1000)' in gauge
mp = mapping['drivers/power/oppo/charger_ic/oppo_mp2650.c'].read_text()
assert '.input_current_write = mp2650_input_current_limit_write' in mp
assert 'return &mp2650_chg_ops' in mp
path = 'drivers/power/oppo/charger_ic/oppo_battery_msm8150_pro.c'
p = research/('stock--'+path.replace('/', '--'))
assert p.exists()
files[path] = {'bytes':p.stat().st_size,'sha256':sha(p)}
usb = p.read_text()
assert 'oppo_chip->vbatt_num == 1' in usb and 'oppo_chip->chg_ops = (oppo_get_chg_ops())' in usb
assert all(v in usb for v in ('USBIN_100MA','USBIN_150MA','USBIN_500MA','USBIN_900MA'))
assert 'smblib_set_usb_suspend(chg, true)' in usb and 'smblib_set_usb_suspend(chg, false)' in usb
provenance = json.loads((w/'reference/kernel76/charging-source-provenance.json').read_text())
# The exact pinned URL and byte hash are retained by session76.
serialized = json.dumps(provenance)
assert files[path]['sha256'] in serialized and '9668fcdc6ec15be7a10d66f7b93c347829e0fdb6' in serialized
core = (linux/'drivers/power/supply/bq27xxx_battery.c').read_text()
assert '#define bq28z610_dm_regs NULL' in core
assert '[BQ28Z610]  = BQ27XXX_DATA(bq28z610,  0' in core
settings = core[core.index('static void bq27xxx_battery_settings'):core.index('static void bq27xxx_battery_settings')+600]
assert 'if (!di->dm_regs)' in settings
smbx = (linux/'drivers/power/supply/qcom_smbx.c').read_text()
assert 'qcom,pmi8998-charger' in smbx and 'qcom,pm660-charger' in smbx and 'qcom,pm8150b' not in smbx
result = {'stock_commit':manifest['commit'],'checked_stock_files':files,
          'legacy_device_type_used_by_stock':'0xFFA5','cell_query':{'write':'3e7100','read_start':'0x40','read_length':4,'delay_us':1000},
          'stock_vbatt2_selects_external_MP2650_operations':True,
          'stock_USB_input_control_includes_SDP_TypeC_APSD_icl_and_suspend':True,
          'MP2650_input_register_limit_is_not_USB_supply_budget_validation':True,
          'current_bq28_driver_dm_regs_null_unseal_key_zero':True,'BQ28_kernel_path_uses_no_MAC_queries':True,
          'mainline_qcom_smbx_does_not_match_PM8150b':True,
          'qcom_typec_and_vbus_modules_are_not_MP2650_charge_control':True,
          'extended_device_type_2719_to_exact_model_or_firmware_mapping_established':False,
          'no_security_key_material_copied':True}
(ref/'charging-source-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS pinned gauge/MP2650/SMB5 source hashes and command/operations boundaries')
