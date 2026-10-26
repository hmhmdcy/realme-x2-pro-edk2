from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
kernel=m.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text());git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a],text=True)
assert git('rev-parse','HEAD').strip()==state['commit'] and not git('status','--porcelain')
failed=json.loads((P/'intree-build-state.json').read_text());assert failed['terminal'] and failed['exit_code']==2
path='drivers/media/platform/qcom/camss/camss-vfe-175-ds4.c';old=(kernel/path).read_text();new=(HERE/'camss-vfe-175-ds4.c').read_text()
assert new.replace('#include <linux/bits.h>\n','')==old
(kernel/path).write_text(new)
subprocess.run(['git','-C',str(kernel),'add','--',path],check=True);subprocess.run(['git','-C',str(kernel),'commit','-m','media: camss: include bit masks explicitly for DS4 codec'],check=True)
state['include_fix_parent']=state['commit'];state['commit']=git('rev-parse','HEAD').strip();state['first_build_missing_explicit_bits_header_fixed']=True
for row in state['source_hashes']:row['sha256']=hashlib.sha256((kernel/row['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'ds4-register-codec.patch').write_text(git('diff',state['parent_commit'],'HEAD','--','drivers/media/platform/qcom/camss'))
p=HERE/'intree-build-r1-validation.json';d=json.loads(p.read_text());d['actual_in_tree_camss_and_core_candidates_built']=False;p.write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(commit=state['commit'],only_explicit_bits_include_added=True,failed_build_terminal_before_source_change=True)))
