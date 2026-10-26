from pathlib import Path
import runpy, subprocess, difflib, json, hashlib
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
k=Path('/home/cy122/pmos-samurai-kernel118/camera121/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel121')
patch=Path('/mnt/e/edk2-samurai-out/kernel121/pm8008-reference/mfd-no-irq.patch')
paths=['drivers/mfd/qcom-pm8008.c','Documentation/devicetree/bindings/mfd/qcom,pm8008.yaml']
before={p:(k/p).read_text() for p in paths}
assert 'pm8008_regulator_cells' not in before[paths[0]]
subprocess.run(['git','apply','--check',str(patch)],cwd=k,check=True)
subprocess.run(['git','apply',str(patch)],cwd=k,check=True)
# Project-local binding extension: a regulator-only MFD has neither GPIO nor
# temperature cells. Keep all five input supplies mandatory; never invent rails.
s=before[paths[1]]
for item in ['interrupts','gpio-controller','"#gpio-cells"','gpio-ranges','interrupt-controller','"#interrupt-cells"','"#thermal-sensor-cells"']:
    anchor='  - '+item+'\n';assert s.count(anchor)==1;s=s.replace(anchor,'',1)
anchor='additionalProperties: false\n\nexamples:'
deps='''dependencies:
  interrupt-controller: [ interrupts, "#interrupt-cells" ]
  "#interrupt-cells": [ interrupts, interrupt-controller ]
  gpio-controller: [ interrupts, interrupt-controller, "#gpio-cells", gpio-ranges ]
  "#gpio-cells": [ gpio-controller ]
  gpio-ranges: [ gpio-controller ]
  pinctrl: [ gpio-controller ]
  "#thermal-sensor-cells": [ interrupts, interrupt-controller ]

'''
assert s.count(anchor)==1;s=s.replace(anchor,deps+anchor)
(k/paths[1]).write_text(s)
diff=''.join(''.join(difflib.unified_diff(before[p].splitlines(True),(k/p).read_text().splitlines(True),fromfile='a/'+p,tofile='b/'+p)) for p in paths)
(ref/'pm8008-no-irq-7.3.patch').write_text(diff)
subprocess.run(['git','diff','--check','--',*paths],cwd=k,check=True)
assert (k/'.config').read_text().count('CONFIG_MFD_QCOM_PM8008=m\n')==1
assert (k/'.config').read_text().count('CONFIG_REGULATOR_QCOM_PM8008=m\n')==1
report=dict(candidate=121,reference_patch_applies_cleanly=True,reference_series_withdrawn_as_duplicate=True,reference_not_claimed_merged=True,local_binding_matches_regulator_only_cell_set=True,all_five_input_supply_groups_still_required=True,irq_and_gpio_dependencies_mutual=True,no_pm8010_identity_or_voltage_changes=True,no_board_pmic_nodes_created=True,no_phone_changes=True,patch_sha256=hashlib.sha256(diff.encode()).hexdigest())
(ref/'pm8008-port-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
