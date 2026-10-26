from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import collections,hashlib,json,os,re,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
out=root/'k213-libcamera-build';sdk=root/'k213-libcamera-sdk';active=json.loads((out/'active-build-private.json').read_text());assert active['phase']=='compile-helper' and not Path('/proc',str(active['pid'])).exists()
buildenv=json.loads((out/'build-environment-private.json').read_text())
log=(out/'compile-helper-private.log').read_text();assert 'ninja: subcommands failed' in log
(out/'first-link-failure-private.log').write_text(log)
db=Path('/lib/apk/db/installed').read_bytes()
search=[Path('/usr/lib'),Path('/lib')]
ldpath=Path('/etc/ld-musl-aarch64.path')
if ldpath.is_file():search += [Path(n) for n in ldpath.read_text().strip().split(':') if n.startswith('/')]
names=['libyaml-0.so.2','libgnutls.so.30','libevent-2.1.so.7','libevent_pthreads-2.1.so.7','libyuv.so.0','libEGL.so.1','libGLESv2.so.2','libunwind.so.8','libunwind-aarch64.so.8','libdrm.so.2','libgbm.so.1']
actual_yuv=sorted([p for d in search for p in d.glob('libyuv.so*') if p.is_file()],key=lambda p:len(p.name));assert actual_yuv
names[names.index('libyuv.so.0')]=actual_yuv[0].name
queue=collections.deque(names);seen={};missing=[]
while queue:
    name=queue.popleft()
    if name in seen:continue
    matches=[d/name for d in search if (d/name).is_file()]
    if not matches:missing.append(name);continue
    source=matches[0];data=source.read_bytes();seen[name]=dict(path=str(source),sha256=hashlib.sha256(data).hexdigest())
    result=subprocess.run([str(sdk/'usr/bin/readelf'),'-d',str(source)],capture_output=True,text=True,check=True,timeout=15,env=buildenv)
    queue.extend(re.findall(r'\(NEEDED\).*?\[([^\]]+)\]',result.stdout))
    for target in {sdk/'usr/lib'/name,sdk/'usr/lib'/source.resolve().name}:
        if target.is_symlink():target.unlink()
        target.write_bytes(data)
assert not missing,missing
for name,record in seen.items():assert hashlib.sha256((sdk/'usr/lib'/name).read_bytes()).hexdigest()==record['sha256']
assert db==Path('/lib/apk/db/installed').read_bytes()
(out/'recursive-runtime-closure-private.json').write_text(json.dumps(seen,indent=2)+'\n')
warnings=[line for line in log.splitlines() if 'warning:' in line or 'not found' in line][:12]
print(json.dumps(dict(stage=213,recursive_dt_needed_runtime_closure_copied_to_sdk_only=True,runtime_libraries=len(seen),all_copied_libraries_match_actual_system=True,package_database_unchanged=True,first_link_failure_preserved=True,linker_warnings=warnings,no_product_camera_library_replacement=True)))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=120);(host.PRIVATE/'sdk-runtime-repair-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'sdk-runtime-repair-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
