from pathlib import Path
import hashlib,importlib.util,json,re
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
root=storage.mounted_build().parent/'source354';header='include/dt-bindings/clock/qcom,sm8150-camcc.h';driver='drivers/clk/qcom/camcc-sm8150.c'
a=(root/header).read_text();b=(root/driver).read_text();identifier=int(re.search(r'#define CAM_CC_ICP_BCR\s+(\d+)',a)[1]);offset=int(re.search(r'\[CAM_CC_ICP_BCR\]\s*=\s*\{\s*(0x[0-9a-f]+)',b)[1],16)
assert identifier==9 and offset==0xc0b4
report=dict(stage=373,header=header,driver=driver,source_hashes={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in [header,driver]},
 reset_id=identifier,reset_register_offset=hex(offset),static_and_diagnostic_dt_reset_id_matches=True,no_reset_binding_change_applied=True)
(HERE/'reset-id-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
