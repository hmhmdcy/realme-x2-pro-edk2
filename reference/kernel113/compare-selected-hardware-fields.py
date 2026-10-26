from pathlib import Path
import json

out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
fields=json.loads((out/'config-reference-hardware-fields-private.json').read_text())
old=fields['original/msmnile_lsm6ds3c.json']
reference=fields['lineage18/msmnile_lsm6ds3c_19781.json']
extract=lambda properties:{key.rsplit('/',1)[-1]:value['data'] for key,value in properties.items()
    if '/.config/' in key}
original_hw=extract(old); reference_hw=extract(reference)
assert len(original_hw)==len(reference_hw)==14
ram=json.loads((out/'ram-v7-hardware-properties-private.json').read_text())
selected=ram['selected_bus_power_properties']['lsm6ds3c_0_platform.config']
equal=original_hw==reference_hw
ram_equal=all(str(selected[key])==value for key,value in reference_hw.items())
assert equal and ram_equal
report=dict(sensor='lsm6ds3c',reference_commit='b94e26044cb95092add5dd8026fab0fdcb61433a',
    hardware_properties_compared=14,original_and_same_model_reference_bus_irq_power_match=equal,
    actual_generated_ram_v7_configuration_matches=ram_equal,
    original_soc339_filter_matches_live_soc339=True,
    reference_soc339_filter_matches_live_soc339=True,
    simple_wrong_spi_instance_irq_or_rail_configuration_supported=False,
    all_configuration_selection_proven_correct=False,spi_client_failure_fixed=False,
    calibration_values_compared_or_imported=False,phone_configuration_changed=False)
(ref/'lsm6ds3c-config-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
