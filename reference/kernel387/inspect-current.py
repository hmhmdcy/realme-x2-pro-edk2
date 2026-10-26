from pathlib import Path
import hashlib,importlib.util,json,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
build=storage.mounted_build();kernel=build.parent/'source354';library=build.parent/'libcamera362-serialized-built/src/libcamera-v0.7.2'
git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a],text=True).strip()
assert git('rev-parse','HEAD')=='ab58f554a7b9f886bd43b9c3f47d52761d9bf982' and not git('status','--porcelain')
names=['src/libcamera/pipeline/camss-vfe/camss_vfe.cpp','src/libcamera/pipeline/camss-vfe/meson.build',
 'include/libcamera/internal/v4l2_videodevice.h','src/libcamera/v4l2_videodevice.cpp','src/libcamera/pipeline_handler.cpp']
rows=[]
for name in names:
 p=library/name;target=P/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
 rows.append(dict(path=name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
assert rows[0]['sha256']=='3806f439548bb99f60046477d24e527cd3d8f51cfb7b8402ff484fdae45cc5fd'
assert rows[-1]['sha256']=='96b1fe8396c956172718808d0d5a21a746379b1c78daf8edaa3c2e2614825f3c'
code="""from pathlib import Path
import json
print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),kernel=Path('/proc/sys/kernel/osrelease').read_text().strip(),
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
 candidates_absent=not any(Path('/sys/module',n).exists() for n in ['qcom_camss_icp_a5_core','camss_icp_a5_boot_test','camss_icp_a5_m2m','v4l2_mem2mem']),
 firmware_absent=not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists())))
"""
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
assert d['taint']==0 and d['candidates_absent'] and d['firmware_absent'] and all(v=='suspended' for v in d['camera_pm'].values())
report=dict(stage=387,kernel_source=str(kernel),kernel_commit=git('rev-parse','HEAD'),library_baseline=str(library),
 relevant_library_files=rows,guard378_verified=True,phone_mutated=False,**d,passed=True)
(HERE/'initial-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='relevant_library_files'},indent=2))
