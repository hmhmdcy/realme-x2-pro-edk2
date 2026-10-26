"""Freeze this offline package receipt; does not run any updater or default test."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def main():
    tests=json.loads((HERE/'test-result.json').read_bytes());result=json.loads((HERE/'payload-result.json').read_bytes())
    assert tests['passed'] is True and tests['affected_packaging_checks']==7 and result['passed'] is True
    for name,digest in tests['tested_files'].items():assert sha((HERE/name).read_bytes())==digest,name
    assert result['old_manifest_sha256']=='5fca8e5a0795325bd780b7965579068c7edc35fa7da12bac357bb30bbde69417'
    assert result['forward_files']['/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko']=='97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd'
    for direction in ('forward','rollback'):
        row=result[direction];raw=Path(row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
    assert result['original_inputs_unchanged'] and result['all_other_manifest_bytes_and_entries_unchanged']
    names=['package.py','test-package.py','test-result.json','payload-result.json','execution-receipt.json','README.md','freeze.py']
    delivery={'schema':'samurai-charger-reattach-two-file-package-delivery-v1','passed':True,'frozen':True,
       'files':{name:{'sha256':sha((HERE/name).read_bytes()),'bytes':len((HERE/name).read_bytes())} for name in names},
       'forward':result['forward'],'rollback':result['rollback'],'new_manifest_sha256':result['new_manifest_sha256'],
       'affected_packaging_checks':7,'old_matrices_or_default_tests_rerun':False,'deployable_transaction_created':False,
       'r8_updater_directly_usable':False,'device_or_SDK_or_284_accessed':False,'protection_reloaded_or_MAC_attempt_reset':False}
    raw=(json.dumps(delivery,indent=2)+'\n').encode()
    with (HERE/'delivery.json').open('xb') as stream:stream.write(raw)
    print(json.dumps({'passed':True,'delivery_sha256':sha(raw)}))

if __name__=='__main__':main()
