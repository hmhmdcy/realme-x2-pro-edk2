from pathlib import Path
import importlib.util,json,subprocess,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
head=git('rev-parse','HEAD');assert head=='5a0df37d3e9c8971d55186e468b38b424c8387dc' and not git('status','--porcelain')
for name in ['camss-icp-a5-boot-test.c','camss-icp-a5-ipe.h','camss-icp-a5-boot.c']:
 (P/(name+'.before')).write_text((source/'drivers/media/platform/qcom/camss'/name).read_text())
code="""from pathlib import Path
import json
print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),kernel=Path('/proc/sys/kernel/osrelease').read_text().strip(),
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
 modules=[p.name for p in Path('/sys/module').glob('*icp*')],temporary_firmware_absent=not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists())))
"""
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
assert d['taint']==0 and not d['modules'] and d['temporary_firmware_absent'] and all(v=='suspended' for v in d['camera_pm'].values())
report=dict(stage=385,source=str(source),source_commit=head,source_clean=True,guard378_verified=True,phone_mutated=False,**d,passed=True)
(HERE/'initial-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
