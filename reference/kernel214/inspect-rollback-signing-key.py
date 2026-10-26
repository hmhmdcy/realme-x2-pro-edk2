from pathlib import Path
import json,tarfile
private=Path('/mnt/e/edk2-samurai-out/kernel214');cache=json.loads((private/'rollback-apk-cache-private.json').read_text());path=Path(next(r['path'] for r in cache if r['file'].startswith('libcamera-99990.7.2-r4.')))
with tarfile.open(path,'r:gz',ignore_zeros=True) as archive:signatures=[p.name for p in archive.getmembers() if p.name.startswith('.SIGN.')]
assert len(signatures)==1;name=signatures[0].split('.',3)[-1];assert name.endswith('.pub') and Path(name).name==name
locations=[Path('/home/cy122/pmos-samurai-rootfs01/work/config_abuild'),Path('/home/cy122/pmos-samurai-rootfs01/work/config_apk_keys'),Path('/home/cy122/pmos-samurai-rootfs01/work/chroot_native/etc/apk/keys'),Path('/home/cy122/.abuild')]
matches=[]
for root in locations:
    if root.is_dir():matches.extend(str(p) for p in root.rglob(name) if p.is_file())
record=dict(signature_member=signatures[0],public_key_name=name,matching_existing_build_public_keys=matches,phone_trust_has_key=(private/'phone-trusted-public-keys'/name).exists())
(private/'rollback-original-signing-key-private.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(original_signature_keys=1,matching_retained_build_public_keys=len(matches),phone_global_trust_has_original_key=record['phone_trust_has_key'])))
