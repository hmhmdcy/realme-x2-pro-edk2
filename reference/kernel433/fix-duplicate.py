from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('storage433duplicate',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);kernel=m.mounted_build().parent/'source354';camss=Path('drivers/media/platform/qcom/camss');state=json.loads((HERE/'source-state.json').read_text())
git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a],text=True).strip();assert git('rev-parse','HEAD')==state['commit'] and not git('status','--porcelain')
for name in ['camss-vfe-175-gtm.c','camss-vfe-175-gtm.h']:(kernel/camss/name).write_bytes((HERE/name).read_bytes())
p=kernel/camss/'camss-vfe-17x.c';t=p.read_text();old='\treturn ret ?: vfe_175_ds4_validate_line(line, params);';new='\tret = ret ?: vfe_175_ds4_validate_line(line, params);\n\treturn ret ?: vfe_175_gtm_validate_buffer(params);';assert t.count(old)==1;p.write_text(t.replace(old,new))
subprocess.run(['git','-C',str(kernel),'diff','--check'],check=True);subprocess.run(['git','-C',str(kernel),'add','--',str(camss)],check=True);subprocess.run(['git','-C',str(kernel),'commit','-m','media: camss: reject repeated GTM transactions in one parameter buffer'],check=True)
state['commit']=git('rev-parse','HEAD');state['duplicate_gtm_per_buffer_rejected']=True
for row in state['source_hashes']:row['sha256']=hashlib.sha256((kernel/row['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'gtm-driver.patch').write_text(subprocess.check_output(['git','-C',str(kernel),'diff','--binary',state['parent_commit'],'HEAD'],text=True));print(json.dumps(dict(commit=state['commit'],passed=True)))
