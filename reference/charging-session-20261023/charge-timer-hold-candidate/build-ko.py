"""Reuse the existing single-charger builder, changing only verified inputs."""
from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'charger-reattach-observation-module-candidate/build-ko.py'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('timer_hold_existing_single_ko_builder',OLD)
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
original_source_inputs=builder.source_inputs
old_paths=original_source_inputs()
old_ko=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charger-reattach-observation-module-private-01/samurai-mp2650-reattach-observation-private.ko')
assert sha(old_ko)=='97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd'
old_ko_before=sha(old_ko)
delivery=HERE/'delivery.json';pin=sha(delivery)
def source_inputs():
    value=json.loads(delivery.read_bytes());assert value['passed'] and sha(delivery)==pin
    for name,row in value['files'].items():assert sha(HERE/name)==row['sha256']
    assert json.loads((HERE/'test-result.json').read_bytes())['passed']
    result=dict(old_paths)
    result['samurai-mp2650.c']=HERE/'samurai-mp2650.c'
    result['charge-cycle-hold.h']=HERE/'charge-cycle-hold.h'
    baseline=json.loads((HERE/'source-result.json').read_bytes())
    assert sha(old_paths['samurai-mp2650.c'])==baseline['baseline_C_sha256']
    assert all(sha(old_paths[n])==digest for n,digest in baseline['unchanged_headers'].items())
    return result
builder.HERE=HERE;builder.AUTHOR=HERE;builder.AUTHOR_DELIVERY=pin
builder.OUT=Path('/home/cy122/charging-management-20261023/charge-timer-hold-module-01')
builder.EXPORT=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charge-timer-hold-module-private-01')
builder.source_inputs=source_inputs
if __name__=='__main__':
    try:builder.main()
    finally:assert sha(old_ko)==old_ko_before
