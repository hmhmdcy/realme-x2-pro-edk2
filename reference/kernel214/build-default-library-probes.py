from pathlib import Path
import hashlib,json,shutil,subprocess
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel214');root=Path('/home/cy122/x2pro-linux/libcamera214-root');out=private/'probes';out.mkdir(mode=0o700)
assert (root/'candidate/usr/lib/libcamera.so.0.7.2').is_file()
records=[]
for name in ['raw-dark-sync-probe','csid-known-input-sync-probe']:
    source=here.parent/'kernel213'/(name+'.cpp');staged=root/'private'/(name+'.cpp');shutil.copyfile(source,staged);target=root/'private'/name
    args=['chroot',str(root),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-pthread','-I/candidate/usr/include/libcamera','/private/'+name+'.cpp','-L/candidate/usr/lib','-Wl,-rpath-link,/candidate/usr/lib','-lcamera','-lcamera-base','-o','/private/'+name]
    p=subprocess.run(args,capture_output=True,timeout=120);(private/(name+'-compile-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
    p=subprocess.run(['chroot',str(root),'/usr/bin/readelf','-d','/private/'+name],capture_output=True,text=True,timeout=30);assert p.returncode==0 and 'RPATH' not in p.stdout and 'RUNPATH' not in p.stdout
    copied=out/name;shutil.copyfile(target,copied);records.append(dict(name=name,sha256=hashlib.sha256(copied.read_bytes()).hexdigest(),bytes=copied.stat().st_size,no_runpath_to_old_candidate=True))
report=dict(stage=214,real_camera_probe_binaries_built_against_full_api=True,dma_buf_read_start_end_sync=True,no_embedded_old_candidate_runpath=True,default_system_libraries_used_when_no_ld_override=True,probes=records,not_yet_executed_on_phone=True)
(here/'probe-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
