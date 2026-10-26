from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;boot=json.loads((HERE.parent/'kernel389/build-package-validation.json').read_text());manifest=json.loads((P.parent/'kernel389/module-stage-manifest-private.json').read_text())
proof=json.loads((P/'preflight-private.json').read_text());oldnotes=json.loads((P.parent/'kernel388/sg-runtime-baseline-private.json').read_text())
code=r'''from pathlib import Path
import hashlib,json,os
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
root=Path('/var/lib/samurai/k390-deployment');s=json.loads((root/'state.json').read_text());assert s['terminal'] and s['passed']
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'boot-id-private.txt').read_bytes()
assert sha('/dev/disk/by-partlabel/boot')==BOOT and sha('/dev/disk/by-partlabel/logdump')==LOGDUMP
for n,row in OLDNOTES.items():assert sha('/sys/module/'+n+'/notes/.note.gnu.build-id')==row['note_sha256']
meta=MANIFEST;modroot=Path(MODROOT)
for r in meta['modules']:assert sha(modroot/r['target_relative'])==r['sha256']
assert sha(meta['firmware']['target'])==meta['firmware']['sha256']
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert all(Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci'])
assert not any(Path('/sys/module',n).exists() for n in ['qcom_camss_icp_a5_core','camss_icp_a5_m2m','camss_icp_a5_boot_test','v4l2_mem2mem'])
print(json.dumps(dict(stage=390,boot_and_logdump_match_retained_rollback=True,candidate_module_and_firmware_files_verified=True,old_loaded_code_still_active=True,camera_idle=True,taint=0,passed=True)))
'''.replace('BOOT',repr(boot['rollback_boot_sha256'])).replace('LOGDUMP',repr(json.loads((HERE.parent/'kernel365/boot-package-validation.json').read_text())['logdump_sha256'])).replace('OLDNOTES',repr(oldnotes)).replace('MANIFEST',repr(manifest)).replace('MODROOT',repr(proof['module_root']))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=30);(HERE/'pre-transition-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
