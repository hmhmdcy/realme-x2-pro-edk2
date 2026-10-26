from pathlib import Path
import hashlib,json,re,subprocess,tarfile
import host
R=Path(__file__).parent;repo=R.parents[1];recipe=repo/'linux-port/packages/pipewire-common';SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire265-retained-busy';work=Path('/home/cy122/x2pro-linux/pipewire265-recipe-qa');assert not work.exists();work.mkdir()
lock=json.loads((recipe/'source-lock.json').read_text());text=(recipe/'APKBUILD').read_text();archive=host.PRIVATE.parent/'kernel262/source/pipewire-1.6.9.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==lock['source_tar']['sha256']
checks=re.findall(r'^([0-9a-f]{128})  (\S+)$',text,re.M);assert len(checks)==12
for digest,name in checks:assert hashlib.sha512((archive if name=='pipewire-1.6.9.tar.gz' else recipe/name).read_bytes()).hexdigest()==digest,name
with tarfile.open(archive) as a:
 for m in a:assert (m.name=='pipewire-1.6.9' or m.name.startswith('pipewire-1.6.9/')) and '..' not in Path(m.name).parts
 a.extractall(work,filter='data')
source=work/'pipewire-1.6.9';queue=['systemd-units-wo-libsystemd.patch',*lock['patch_sha256']];logs=[]
for name in queue:
 q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-d',str(source)],input=(recipe/name).read_bytes(),capture_output=True);logs.append(q.stdout+q.stderr);assert q.returncode==0,(name,(q.stdout+q.stderr).decode())
(host.PRIVATE/'recipe-r3-prepare-private.log').write_bytes(b'\n'.join(logs))
expected={'src/pipewire/impl-port.c':SDK/'work/pipewire263-broadcast/pipewire-1.6.9/src/pipewire/impl-port.c','src/pipewire/mem.c':W/'core-map-lookup/mem.c','src/pipewire/mem.h':W/'core-map-lookup/mem.h','spa/plugins/libcamera/libcamera-source.cpp':SDK/'work/pipewire265-fresh-allocation/source/libcamera-source.cpp',**{'src/gst/'+n:W/'v4/source'/n for n in ['gstpipewirepool.h','gstpipewirepool.c','gstpipewiresrc.c']}}
for name,p in expected.items():assert (source/name).read_bytes()==p.read_bytes(),name
assert subprocess.run(['sh','-n',str(recipe/'APKBUILD')],capture_output=True).returncode==0
report=dict(stage=265,version='1.6.9-r3',pristine_archive_sha256_verified=True,source_checksums_verified=len(checks),patches_applied_without_fuzz=len(queue),all_seven_build_inputs_match_deployed_source=True,apkbuild_shell_syntax_passed=True,full_abuild_build_executed=False)
(R/'recipe-prepare-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

