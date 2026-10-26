from pathlib import Path
import importlib.util,json,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
k=m.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(k),*a],text=True)
assert git('rev-parse','HEAD').strip()=='a993cd8a1db892bb5d68d9e6bcccfcc048aec9fd' and not git('status','--porcelain')
assert json.loads((P.parent/'kernel427/intree-build-state.json').read_text())['terminal']
code='''from pathlib import Path
import json
dev=Path('/sys/bus/platform/devices/ac10000.icp')
print(json.dumps(dict(same394=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),core=json.loads((dev/'state').read_text()),m2m=json.loads((dev/'m2m_status').read_text()),workers=[dict(root=p.parent.name,terminal=json.loads(p.read_text())['terminal']) for p in Path('/var/lib/samurai').glob('k427-ds4-r*/state.json')],services={n:len([p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()==n and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z']) for n in ['pipewire','wireplumber']})))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);q.check_returncode();(P/'device-before-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
assert d['same394'] and d['taint']==512 and all(w['terminal'] for w in d['workers']) and d['services']==dict(pipewire=1,wireplumber=1)
assert d['m2m']['jobs']==d['m2m']['failed']==d['m2m']['cancelled']==0
print(json.dumps(dict(source=git('rev-parse','HEAD').strip(),device=d),indent=2))
