from pathlib import Path
import importlib.util,json,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';parent=json.loads((HERE.parent/'kernel371/source-state.json').read_text())['commit']
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
for name in ['camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-boot-test.c']:
 (P/(name+'.before')).write_bytes((source/'drivers/media/platform/qcom/camss'/name).read_bytes())
code='''from pathlib import Path
import json
print(json.dumps(dict(kernel=Path('/proc/sys/kernel/osrelease').read_text().strip(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 camss=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip(),
 core_absent=not Path('/sys/module/qcom_camss_icp_a5_core').exists(),test_absent=not Path('/sys/module/camss_icp_a5_boot_test').exists())))
'''
facts=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
assert facts['taint']==0 and facts['camss']=='suspended' and facts['core_absent'] and facts['test_absent']
report=dict(stage=372,source_commit=parent,source_clean=True,current371_guard_verified=True,**facts,passed=True)
(HERE/'preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
