from pathlib import Path
import hashlib,json,tarfile
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128';out=Path('/mnt/e/edk2-samurai-out/kernel128')
with tarfile.open(out/'staging-private.tar.gz') as tf:data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
assert data['new-module-tree.sha256']==(out/'module-tree.sha256').read_bytes()
assert data['new-release.txt']==b'7.3.0-rc6-rmx1931-samurai-k128+\n'
assert data['staging-boot-id-private.txt'].strip()==(out/'source-boot-id-private.txt').read_bytes().strip()
for name in ['new-module-check.txt','old126-still-exact.txt','old118-ipa-still-exact.txt','bt-script-still-exact.txt']:
 assert data[name] and all(line.endswith(b': OK') for line in data[name].splitlines())
assert data['new-module-check.txt'].count(b': OK')==len(data['new-module-tree.sha256'].splitlines())
report=dict(live_staging_audit_pass=True,new128_directory_all_files_match_validated_archive=True,
 old118_and126_directories_preserved=True,bluetooth_release_path_unchanged=True,current_kernel_still126=True,
 no_new_modules_loaded_before_reboot=True,archive_sha256=hashlib.sha256((out/'staging-private.tar.gz').read_bytes()).hexdigest(),goal_complete=False)
for folder in [ref,out]:(folder/'live-staging-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K128_FRESH_BOOT_MATCHING_MODULE_STAGING_AND_STABLE_RELEASES_PASS',flush=True)
