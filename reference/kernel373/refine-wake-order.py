from pathlib import Path
import difflib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
old='''\tret = program_hfi_parameters(a5);
\tif (!ret) {
\t\twritel(A5_ENABLE | A5_WAKE | A5_WFI_GATE, base + A5_CONTROL);
\t\twritel(1, base + A5_INIT_REQUEST);
\t}'''
new='''\twritel(A5_ENABLE | A5_WAKE | A5_WFI_GATE, base + A5_CONTROL);
\tret = program_hfi_parameters(a5);
\tif (!ret)
\t\twritel(1, base + A5_INIT_REQUEST);'''
s=(P/'boot-proposed.c').read_text();assert s.count(old)==1;s=s.replace(old,new)
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text());relative=state['relative']
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==state['commit'] and not git('status','--porcelain')
assert (source/relative).read_bytes()==(P/'boot-proposed.c').read_bytes()
(P/'boot-proposed.c').write_text(s);(source/relative).write_text(s)
subprocess.run(['git','-C',str(source),'diff','--check'],check=True);subprocess.run(['git','-C',str(source),'add','--',relative],check=True)
subprocess.run(['git','-C',str(source),'commit','-m','media: camss: wake A5 before programming cold-boot HFI registers'],check=True,capture_output=True)
state['intermediate_commit']=state['commit'];state['commit']=git('rev-parse','HEAD');(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
(HERE/'hfi-reset-order.patch').write_text(''.join(difflib.unified_diff((P/'boot-before.c').read_text().splitlines(True),s.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
# Keep the original proposal generator reproducible at the final sequence.
generator=(HERE/'prepare-proposal.py').read_text();old_literal=old.replace('\t','\\t');new_literal=new.replace('\t','\\t')
if old_literal in generator:(HERE/'prepare-proposal.py').write_text(generator.replace(old_literal,new_literal))
else:assert new_literal in generator
print(json.dumps(dict(stage=373,commit=state['commit'],wake_before_hfi_programming=True,firmware_cpu_started=False)))
