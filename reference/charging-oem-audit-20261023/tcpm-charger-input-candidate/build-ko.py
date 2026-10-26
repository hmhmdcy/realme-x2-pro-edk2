"""Reuse the installed charger baseline builder; build one new module only."""
from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
PREVIOUS=REF/'charging-session-20261023/charge-timer-hold-r2-candidate/build-ko.py'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('existing_timer_hold_r2_builder',PREVIOUS)
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
baseline_inputs=previous.source_inputs()
assert sha(baseline_inputs['samurai-mp2650.c'])=='32fa5840d28fd5cbe7366e8d0951e9cd20b87dff6263d49d3386cd3a3e486ed6'
baseline_ko=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charge-timer-hold-module-private-02/samurai-mp2650-reattach-observation-private.ko')
assert sha(baseline_ko)=='bef4dba73e1244fec4c89f2d5b47ac6b1483384c1f64aa1d589de792d2e97d6f'
delivery=HERE/'delivery.json'
pin=sha(delivery)

def source_inputs():
    value=json.loads(delivery.read_bytes());assert value['passed'] and sha(delivery)==pin
    for name,row in value['files'].items():assert sha(HERE/name)==row['sha256']
    assert json.loads((HERE/'test-result.json').read_bytes())['passed']
    result=dict(baseline_inputs)
    result['samurai-mp2650.c']=HERE/'samurai-mp2650.c'
    result['negotiated-input.h']=HERE/'negotiated-input.h'
    return result

builder=previous.builder
builder.HERE=HERE;builder.AUTHOR=HERE;builder.AUTHOR_DELIVERY=pin
builder.OUT=Path('/home/cy122/charging-management-20261023/tcpm-charger-input-module-01')
builder.EXPORT=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/tcpm-charger-input-module-private-01')
builder.source_inputs=source_inputs
if __name__=='__main__':
    try:builder.main()
    finally:assert sha(baseline_ko)=='bef4dba73e1244fec4c89f2d5b47ac6b1483384c1f64aa1d589de792d2e97d6f'
