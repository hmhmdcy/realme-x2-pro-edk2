"""Only freeze actual packaging receipts; never packages, builds or activates."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((H/'logdump-result.json').read_bytes());p=json.loads((H/'Image502-pins.json').read_bytes())
reuse=json.loads((H/'reuse-result.json').read_bytes());io=json.loads((H/'bounded-read-result.json').read_bytes())
assert r['passed'] and r['host_linux_pid']==955 and r['Image502_sha256']==p['Image_sha256']
for key in ['only_Image_file_changed','other_entries_and_contents_exact','all_non_Image_bytes_exact','Image_readback_exact','fsck_readonly_passed','parent_inputs_unchanged','parent_mountinfo_unchanged','no_device_or_deployment']:assert r[key],key
assert r['rollback_logdump_sha256']=='7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9'
assert r['logdump_sha256']=='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1' and r['logdump_bytes']==67108864
assert sha(H/'package-logdump.py')==reuse['candidate_sha256']==io['source_sha256']=='1a262316bc43536dcbc0c4305114deff31b9bcb13850e3674829f74ad6ac01e6'
assert reuse['parse_fat_function_unchanged'] and reuse['ranges_and_fsck_sequence_unchanged_after_IO_substitution']
private=Path('E:/edk2-samurai-out/charging-management-20261023/gauge-image502-logdump-private-01')
assert sha(private/'result.json')==r['private_result_sha256']
actual=json.loads((private/'result.json').read_bytes());assert actual['passed']
assert actual['inputs_before']==actual['inputs_after']
assert [x['returncode'] for x in actual['commands']]==[0,0,0]
assert [x['stage'] for x in actual['commands']]==['replace-Image','readback-Image','fsck-readonly']
assert (private/'logdump-gauge502-private.img').stat().st_size==67108864
execution=dict(passed=True,check_local_native_session=92499,check_local_exit=0,check_local_tools_executed=False,
 native_exec_session=22669,linux_pid=955,exit_code=0,same_original_exec_handle_waited=True,
 packaging_invocations=1,source_sha256=sha(H/'package-logdump.py'),no_device_or_activation=True)
(H/'execution-receipt.json').write_text(json.dumps(execution,indent=2)+'\n')
d=dict(passed=True,scope='private FAT /Image502 replacement only; not deployed',
 files={str(x.relative_to(H)).replace('\\','/'):sha(x) for x in sorted(H.rglob('*')) if x.is_file() and x.name!='delivery.json'},
 candidate=dict(path='E:/edk2-samurai-out/charging-management-20261023/gauge-image502-logdump-private-01/logdump-gauge502-private.img',bytes=r['logdump_bytes'],sha256=r['logdump_sha256']),
 rollback=dict(path='E:/edk2-samurai-out/charging-management-20261023/gauge-image501-logdump-private-01/logdump-gauge501-private.img',bytes=67108864,sha256=r['rollback_logdump_sha256']),
 Image502=dict(bytes=p['Image_bytes'],sha256=p['Image_sha256'],source_sha256=p['source_sha256']),
 unchanged_boot_sha256='97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695',
 FAT_DTB_sha256='a82383fa30609bb5e1400f8af12055abdbca7373734c983549d9f437afae2cc5',
 frozen_build_delivery_sha256=p['delivery_sha256'],private_result_sha256=r['private_result_sha256'],
 kernel_build_or_ABI_rerun=False,device_or_SDK_or_Git_used=False,physical_latency_validated=False)
(H/'delivery.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(passed=True,delivery_sha256=sha(H/'delivery.json'),result_sha256=sha(H/'logdump-result.json'),candidate_sha256=r['logdump_sha256'])))
