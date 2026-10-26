from pathlib import Path
import hashlib,json
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel193')
current=(k/'.config').read_bytes();old=(k/'.config.old').read_bytes()
assert current.replace(b'# CONFIG_OF_SAMURAI_CCI_BRINGUP is not set\n',b'')==old
(out/'first-build-config-with-disabled-new-option-private').write_bytes(current);(out/'original183-config-private').write_bytes(old)
(k/'.config').write_bytes(old)
for name in ['cci-helper-build-private.log','samurai-cci-bringup-k193-private.ko']:
 p=out/name;dest=out/(name+'.first');assert p.is_file() and not dest.exists();p.rename(dest)
print(json.dumps(dict(first_build_only_added_disabled_new_option=True,original_config_restored=True,config_sha256=hashlib.sha256(old).hexdigest(),first_log_and_module_preserved=True)))
