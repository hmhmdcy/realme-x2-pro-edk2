from pathlib import Path
import difflib,hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;state=json.loads((HERE/'source-state.json').read_text())
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
source=m.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==state['commit'] and not git('status','--porcelain')
paths=['drivers/media/platform/qcom/camss/camss-icp-platform.c','Documentation/devicetree/bindings/media/qcom,sm8150-camss-icp.yaml']
for name in paths:
 p=source/name
 if name not in state['changed']:
  assert not p.exists();dest=P/'changes'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.with_suffix(dest.suffix+'.before').write_text('');state['changed'].append(name)
 p.write_text((HERE/p.name).read_text())
git('diff','--check');git('add','--',*paths);git('commit','-m','media: camss: validate ICP firmware configuration and describe its DT binding')
patch=''
for name in state['changed']:
 p=source/name;old=P/'changes'/name;a=old.with_suffix(old.suffix+'.before').read_text();b=p.read_text();old.write_text(b)
 patch+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+name if a else '/dev/null',tofile='b/'+name))
state.update(commit=git('rev-parse','HEAD'),binding_is_local_proposal=True,sha256={n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in state['changed']})
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'platform-and-board.patch').write_text(patch);print(state['commit'])
