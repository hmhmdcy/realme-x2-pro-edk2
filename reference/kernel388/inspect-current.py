from pathlib import Path
import hashlib,importlib.util,json,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354'
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')=='8003933b7e31e4b5f4d27d21789d42da686831ba' and not git('status','--porcelain')
relative=Path('drivers/media/platform/qcom/camss');rows=[]
for p in sorted((source/relative).glob('*a5*')):
 if p.suffix not in ['.c','.h']:continue
 target=P/'source'/relative/p.name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
 rows.append(dict(path=str(relative/p.name),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
code="""from pathlib import Path
import json
print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),kernel=Path('/proc/sys/kernel/osrelease').read_text().strip(),
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
 candidates_absent=not any(Path('/sys/module',n).exists() for n in ['qcom_camss_icp_a5_core','camss_icp_a5_boot_test','camss_icp_a5_m2m','v4l2_mem2mem']),
 firmware_absent=not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists())))
"""
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
assert d['taint']==0 and d['candidates_absent'] and d['firmware_absent'] and all(v=='suspended' for v in d['camera_pm'].values())
report=dict(stage=388,source=str(source),commit=git('rev-parse','HEAD'),source_clean=True,relevant_files=rows,guard378_verified=True,phone_mutated=False,**d,passed=True)
(HERE/'initial-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='relevant_files'},indent=2));print('\n'.join(r['path'] for r in rows))
