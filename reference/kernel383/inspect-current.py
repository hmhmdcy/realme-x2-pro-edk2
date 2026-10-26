from pathlib import Path
import importlib.util,json,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354'
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')=='47475238dc6a0d4b28a5db22b0c1af223dc50297' and not git('status','--porcelain')
code="""from pathlib import Path
import json
print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),kernel=Path('/proc/sys/kernel/osrelease').read_text().strip(),
 camss=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip(),
 modules=[p.name for p in Path('/sys/module').glob('*icp*')],
 extra_firmware_absent=not any(Path('/lib/firmware/qcom/sm8150',n).exists() for n in ['samurai-icp356.elf','samurai-ipe382-stripe.bin']))))
"""
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
assert d['taint']==0 and d['camss']=='suspended' and not d['modules'] and d['extra_firmware_absent']
report=dict(stage=383,source=str(source),source_commit=git('rev-parse','HEAD'),source_clean=True,guard378_verified=True,phone_mutated=False,**d,passed=True)
(HERE/'initial-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
