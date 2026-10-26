"""Record the diagnosed live-overlay limitation without altering its failure."""
from pathlib import Path
import importlib.util,json
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
overlay=(source/'drivers/of/overlay.c').read_text();private=(source/'drivers/of/of_private.h').read_text()
assert 'if (target->in_livetree)\n\t\tif (is_pseudo_property(overlay_prop->name))\n\t\t\treturn 0;' in overlay
assert '!of_prop_cmp(prop_name, "phandle")' in private
r1=json.loads((HERE/'boot-runtime-r1-validation.json').read_text());r2=json.loads((HERE/'boot-runtime-r2-validation.json').read_text())
assert r1['device_result']['phase']=='resources' and r1['device_result']['error']==-22
assert r2['device_result']['phase']=='firmware-reference' and r2['device_result']['error']==-6
assert all(not r['device_result']['cpu_enabled'] and r['temporary_dt_nodes_absent'] and r['temporary_firmware_removed'] and r['taint_after']==0 for r in [r1,r2])
report=dict(stage=364,offline_merge_passed_but_live_reference_missing=True,
    live_framework_skips_existing_node_phandle_updates=True,
    first_probe_preserved_as_failure=True,second_probe_resolves_no_firmware_node=True,
    a5_cpu_started=False,driver_firmware_region_checks_relaxed=False,
    root_cause='An overlay-local phandle on an __overlay__ root targeting an existing unreferenced board node is not installed in the live tree.',
    correction='Give the disabled SoC ICP node its firmware memory-region in the static board DT, then use that existing reference in temporary diagnostics.',
    passed=True)
(HERE/'live-reference-diagnosis.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
