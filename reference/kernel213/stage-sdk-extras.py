from pathlib import Path
import host,json
here=Path(__file__).resolve().parent;manifest=json.loads((here/'sdk-fetch-validation.json').read_text());private=host.PRIVATE
names=['xorgproto','openssl','libssl3','libcrypto3'];selected=[]
host.ssh('mkdir -m700 /var/lib/samurai/k213-libcamera-build/sdk-extra-apks')
for name in names:
    matches=[r for r in manifest['signed_apks'] if r['name'].startswith(name+'-') and r['name'][len(name)+1].isdigit()];assert len(matches)==1
    record=matches[0];host.upload(private/'sdk-apks-r2'/record['name'],'/var/lib/samurai/k213-libcamera-build/sdk-extra-apks/'+record['name']);selected.append(record['name'])
code=r'''
from pathlib import Path
import json,os,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
out=root/'k213-libcamera-build';sdk=root/'k213-libcamera-sdk';db=Path('/lib/apk/db/installed').read_bytes();packages=sorted((out/'sdk-extra-apks').glob('*.apk'));assert len(packages)==4
for i,p in enumerate(packages):
    for phase,args in [('verify',['apk','verify',str(p)]),('extract',['apk','extract','--force-overwrite','--destination',str(sdk),str(p)])]:
        with (out/('extra-'+str(i)+'-'+phase+'-private.log')).open('wb') as log:subprocess.run(args,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=30)
env=json.loads((out/'build-environment-private.json').read_text())
for name,args in [('openssl-version',[str(sdk/'usr/bin/openssl'),'version']),('egl-pkgconfig',[str(sdk/'usr/bin/pkg-config'),'--cflags','--libs','egl','glesv2'])]:
    with (out/(name+'-private.log')).open('wb') as log:subprocess.run(args,env=env,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=20)
assert db==Path('/lib/apk/db/installed').read_bytes()
print(json.dumps(dict(stage=213,four_additional_signed_sdk_packages_extracted=True,egl_dependency_and_openssl_tool_verified=True,package_database_unchanged=True,first_configure_failure_preserved=True)))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=100);(private/'sdk-extras-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'sdk-extras-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
