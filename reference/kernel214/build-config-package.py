from pathlib import Path
import hashlib,json,os,subprocess
os.umask(0o077);here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel214');root=Path('/home/cy122/x2pro-linux/libcamera214-root');port=repo/'linux-port/packages/samurai-camera-config'
for name in ['configuration.yaml','samurai-camera-heaps.conf','70-samurai-camera-heaps.rules']:
    assert (port/name).read_bytes()==(repo/'linux-port/camera'/name).read_bytes()==(root/'work/samurai-camera-config'/name).read_bytes()
rules=(port/'70-samurai-camera-heaps.rules').read_text();protected=next(line for line in rules.splitlines() if 'KERNEL=="fastrpc-shared-pool"' in line);assert 'GROUP="root"' in protected and 'MODE="0600"' in protected and 'TAG-="uaccess"' in protected
assert not (root/'packages-config').exists()
command=['chroot',str(root),'/usr/bin/env','SOURCE_DATE_EPOCH=1792022400','/bin/ash','-c','cd /work/samurai-camera-config && umask 022 && exec /usr/bin/abuild -F -d -K -P /packages-config all']
with (private/'config-package-build-private.log').open('xb') as log:p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=180)
report=dict(stage=214,abuild_exit=p.returncode,packages=[p.name for p in (root/'packages-config').rglob('*.apk')],configuration_files_match_existing_canonical_payloads=True,protected_fastrpc_rule_verified=True,host_only_no_device_mutation=True)
(private/'config-package-build-result-private.json').write_text(json.dumps(report,indent=2)+'\n');assert p.returncode==0,'Inspect config package build log before repair'
(here/'config-package-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
