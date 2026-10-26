from pathlib import Path
import ast, re, subprocess
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel147')
base=ref.parent / 'kernel146'
out=Path('/mnt/e/edk2-samurai-out/kernel147')
state=(out / 'current146-state-private.txt').read_text().splitlines()
assert state[0].startswith('#146 ')
assert re.fullmatch('[a-f0-9-]{36}',state[1]) and state[2]=='512'
(out / 'source-boot-id-private.txt').write_text(state[1]+'\n')
for name in ['quiesce-current145.sh','freeze-for-bootloader.sh','enter-bootloader.ps1','enable-transition-eud.ps1','flash-ccu-candidate.ps1','check-quiesce.py','collect-preflash.py','run-gpu-probe.py']:
    s=(base / name).read_text().replace('kernel146','kernel147').replace('k146','k147').replace('K146','K147').replace("'^#145 '","'^#146 '").replace("'#145 '","'#146 '").replace('ccu-first','align-first')
    s=s.replace('current_kernel=145,target_kernel=146','current_kernel=146,target_kernel=147').replace('$q.current_kernel -ne 145 -or $q.target_kernel -ne 146','$q.current_kernel -ne 146 -or $q.target_kernel -ne 147').replace('stage=146','stage=147').replace('kernel_build=146','kernel_build=147')
    s=s.replace('logdump-k147-ccu-retire.img','logdump-k147-iova-align.img')
    if name.endswith('.sh'):
        s=s.replace('test "$(cat /proc/sys/kernel/tainted)" = 0','test "$(cat /proc/sys/kernel/tainted)" = 512')
    if name=='collect-preflash.py':
        s=s.replace("read_text().strip()=='0'","read_text().strip()=='512'")
        s=s.replace("assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k147-baseline145/boot-id-private.txt').read_bytes()","assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==Path('/tmp/k147-source-boot-id-private.txt').read_text().strip()")
        s=s.replace("capture(['dmesg'],'dmesg-private.txt')","capture(['dmesg'],'dmesg-private.txt')\nprior=(out / 'dmesg-private.txt').read_text()\nassert prior.count('WARNING:')==1 and 'at wcd934x_comp_probe' in prior\nassert prior.count('gpu fault:')==12")
    if name=='check-quiesce.py':
        s=s.replace("read_text().strip()=='0'","read_text().strip()=='512'").replace("==prior.count('gpu fault:')==2","==prior.count('gpu fault:')==12")
        s=s.replace("assert current.count('WARNING:')==0","assert current.count('WARNING:')==prior.count('WARNING:')==1\nassert 'at wcd934x_comp_probe' in prior")
        s=s.replace('taint=0,','taint=512,').replace('known_baseline_gpu_faults=2','known_baseline_gpu_faults=12')
    dest=ref / name.replace('current145','current146').replace('flash-ccu','flash-align')
    assert not dest.exists(); dest.write_text(s)
    if dest.suffix=='.sh': subprocess.run(['sh','-n',str(dest)],check=True)
    if dest.suffix=='.py': ast.parse(s)
print('K147_CURRENT146_GUARDED_DEPLOYMENT_TOOLS_READY')
