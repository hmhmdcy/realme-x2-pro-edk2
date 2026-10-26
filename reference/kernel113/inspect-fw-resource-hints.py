from pathlib import Path
import hashlib,json,re
private=Path('/mnt/e/edk2-samurai-out')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
root=private/'kernel111/source-files/k111-sensor-sources-readonly'
versions=set(); inventory={}
terms=['lsm6dsm','lsm6ds3c','mmc5603','stk3331','ak099','tcs3701','sns_registry','I2C_QUP_DDR','SPI_QUP_DDR']
for path in sorted((root/'firmware').glob('slpi.*')):
    raw=path.read_bytes()
    versions.update(m.decode('ascii') for m in re.findall(rb'SLPI\.HY\.[A-Za-z0-9._-]+',raw))
    for term in terms:
        inventory[term]=inventory.get(term,0)+raw.lower().count(term.lower().encode())
logs=json.loads((private/'kernel113/ulog-v12-decoded-private.json').read_text())
npa=next(value for name,value in logs.items() if name.startswith('NPA Log@'))
clients={}
for client in ('I2C_QUP_DDR','SPI_QUP_DDR'):
    failures=[line for line in npa if client in line and 'failed client create' in line]
    errors=[int(m) for line in failures for m in re.findall(r'error: (\d+)',line)]
    assert errors==[4],(client,errors)
    clients[client]={'client_create_error_codes':errors,'retained_early_failure':True}
report=dict(firmware_versions=sorted(versions),matching_original_image_string_inventory=inventory,
            early_ulog_v12_npa_client_failures=clients,
            stock_sources_unchanged=True,firmware_configuration_mismatch_proven=False,
            strings_prove_driver_function=False,raw_firmware_and_calibration_private=True,
            sensors_all_accepted=False)
(ref/'firmware-resource-hints.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
