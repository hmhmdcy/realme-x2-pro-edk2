from pathlib import Path
import hashlib,json,os,subprocess,sys
os.umask(0o077);here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel213');retry=sys.argv[1:]==['--r2'];assert not sys.argv[1:] or retry
output=private/('sdk-apks-r2' if retry else 'sdk-apks');output.mkdir(mode=0o700)
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');keys=Path('/home/cy122/pmos-samurai-rootfs01/work/config_apk_keys')
packages=['yaml-dev','gnutls-dev','libevent-dev','libyuv-dev','py3-jinja2','py3-ply','py3-yaml','mesa-dev','libunwind-dev','openssl']
args=[str(apk),'--no-cache','--arch','aarch64','--keys-dir',str(keys),'--repository','https://dl-cdn.alpinelinux.org/alpine/edge/main','--repository','https://dl-cdn.alpinelinux.org/alpine/edge/community','fetch','--recursive','--output',str(output),*packages]
logpath=private/('sdk-fetch-r2-private.log' if retry else 'sdk-fetch-private.log')
with logpath.open('wb') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
assert 'ERROR:' not in logpath.read_text(errors='replace')
assert all(any(output.glob(name+'-[0-9]*.apk')) for name in packages),'Every requested package must actually be fetched'
records=[]
for p in sorted(output.glob('*.apk')):
    q=subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(p)],capture_output=True,timeout=20)
    (private/(p.name+'.signature-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0
    records.append(dict(name=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
assert len(records)>=len(packages)
report=dict(stage=213,requested_development_packages=packages,signed_apks=records,all_signatures_verified=True,no_phone_package_install=True)
(here/'sdk-fetch-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(stage=213,downloaded_signed_packages=len(records),total_bytes=sum(r['bytes'] for r in records),all_signatures_verified=True,no_phone_package_install=True)))
