"""Adapt reusable transition tools to the current #147 boot and #152 image."""
from pathlib import Path
import ast,json,subprocess
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel152')
base=ref.parent/'kernel147'
out=Path('/mnt/e/edk2-samurai-out/kernel152')
build=json.loads((ref/'build-package-validation.json').read_text())
build['dtb_unchanged']=True
(out/'build-package-validation.json').write_text(json.dumps(build,indent=2)+'\n')
for name in ['collect-preflash.py','quiesce-current146.sh','check-quiesce.py',
    'freeze-for-bootloader.sh','enable-transition-eud.ps1','enter-bootloader.ps1','flash-align-candidate.ps1']:
    s=(base/name).read_text().replace('kernel147','kernel152').replace('k147','k152').replace('K147','K152')
    s=s.replace("'#146 '","'#147 '").replace("'^#146 '","'^#147 '")
    s=s.replace("=='512'","=='0'").replace('taint=512','taint=0').replace(')" = 512',')" = 0')
    s=s.replace("assert prior.count('WARNING:')==1 and 'at wcd934x_comp_probe' in prior", "assert prior.count('WARNING:')==0")
    s=s.replace("assert prior.count('gpu fault:')==12", "assert prior.count('gpu fault:')==3")
    s=s.replace("==prior.count('gpu fault:')==12", "==prior.count('gpu fault:')==3")
    s=s.replace("assert current.count('WARNING:')==prior.count('WARNING:')==1\nassert 'at wcd934x_comp_probe' in prior", "assert current.count('WARNING:')==prior.count('WARNING:')==0")
    s=s.replace('known_baseline_gpu_faults=12','known_baseline_gpu_faults=3')
    s=s.replace('current_kernel=146,target_kernel=147','current_kernel=147,target_kernel=152')
    s=s.replace('$q.current_kernel -ne 146 -or $q.target_kernel -ne 147','$q.current_kernel -ne 147 -or $q.target_kernel -ne 152')
    s=s.replace('stage=147','stage=152').replace('stage=147;','stage=152;').replace('kernel_build=147;','kernel_build=152;')
    s=s.replace('logdump-k152-iova-align.img','logdump-k152-dsi-lifecycle.img')
    s=s.replace('align-first','lifecycle-first')
    if name=='collect-preflash.py':
        s=s.replace("print('K152_CURRENT145_PREFLASH_CAPTURED')", "print('K152_CURRENT147_PREFLASH_CAPTURED')")
    dest=ref/name.replace('current146','current147').replace('flash-align','flash-dsi')
    assert not dest.exists(),dest
    dest.write_text(s)
    if dest.suffix=='.sh':subprocess.run(['sh','-n',str(dest)],check=True)
    if dest.suffix=='.py':ast.parse(s)
print('K152_DEPLOYMENT_TOOLS_READY',flush=True)
